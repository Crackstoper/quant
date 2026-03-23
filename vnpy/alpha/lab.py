import json
import shelve
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from functools import lru_cache
from datetime import datetime, date
import polars as pl

from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from vnpy.trader.utility import extract_vt_symbol

from .logger import logger
from .dataset import AlphaDataset, to_datetime
from .model import AlphaModel


def calculate_bollinger_bands(
    df: pl.DataFrame,
    period: int = 20,
    std_dev: float = 2.0
) -> pl.DataFrame:
    """
    计算布林带指标

    Args:
        df: 包含价格数据的DataFrame，必须包含datetime和close列
        period: 移动平均周期，默认20
        std_dev: 标准差倍数，默认2.0

    Returns:
        包含布林带上轨、中轨、下轨的DataFrame，包含以下列：
        - datetime: 时间戳
        - upper_band: 上轨 (SMA + std_dev * std)
        - middle_band: 中轨 (SMA)
        - lower_band: 下轨 (SMA - std_dev * std)

    Example:
        >>> bb_df = calculate_bollinger_bands(price_df, period=20, std_dev=2.0)
    """
    if df.is_empty():
        return pl.DataFrame({
            "datetime": [],
            "upper_band": [],
            "middle_band": [],
            "lower_band": []
        })

    # Ensure datetime column exists
    if "datetime" not in df.columns:
        raise ValueError("DataFrame must contain 'datetime' column")

    # Calculate rolling statistics
    result_df = df.select([
        pl.col("datetime")
    ]).with_columns([
        # Moving Average (中轨)
        pl.col("close").rolling_mean(window_size=period).alias("middle_band"),
        # Standard Deviation
        pl.col("close").rolling_std(window_size=period).alias("std_dev"),
    ])

    # Calculate bands
    result_df = result_df.with_columns([
        # Upper Band (上轨): MA + std_dev * std
        (pl.col("middle_band") + std_dev * pl.col("std_dev")).alias("upper_band"),
        # Lower Band (下轨): MA - std_dev * std
        (pl.col("middle_band") - std_dev * pl.col("std_dev")).alias("lower_band"),
    ])

    # Select final columns
    result_df = result_df.select([
        "datetime",
        "upper_band",
        "middle_band",
        "lower_band"
    ])

    return result_df


class AlphaLab:
    """
    Alpha研究实验室

    功能：
    - 管理数据路径和文件结构
    - 保存和加载K线数据、布林带指标数据、成分股数据、数据集、模型、信号等
    - 提供合约交易配置管理
    - 支持缓存机制提高性能
    - 技术指标计算和保存（如布林带）
    """

    def __init__(self, lab_path: str) -> None:
        """
        构造函数

        Args:
            lab_path: 实验室数据根路径

        功能：
        - 初始化实验室数据路径结构
        - 创建必要的文件夹（daily、minute、component等）
        - 设置数据集、模型、信号等子目录
        """
        # Set data paths
        self.lab_path: Path = Path(lab_path)

        self.daily_path: Path = self.lab_path.joinpath("daily")
        self.minute_path: Path = self.lab_path.joinpath("minute")
        self.component_path: Path = self.lab_path.joinpath("component")

        self.dataset_path: Path = self.lab_path.joinpath("dataset")
        self.model_path: Path = self.lab_path.joinpath("model")
        self.signal_path: Path = self.lab_path.joinpath("signal")

        self.contract_path: Path = self.lab_path.joinpath("contract.json")

        # Create folders
        for path in [
            self.lab_path,
            self.daily_path,
            self.minute_path,
            self.component_path,
            self.dataset_path,
            self.model_path,
            self.signal_path
        ]:
            if not path.exists():
                path.mkdir(parents=True)

    def save_bar_data(self, bars: list[BarData]) -> None:
        """
        保存K线数据

        Args:
            bars: K线数据列表

        功能：
        - 根据K线数据的周期（日线、分钟线）保存到对应文件夹
        - 支持数据去重和追加写入
        - 使用Parquet格式存储提高读取效率
        """
        if not bars:
            return

        # Get file path
        bar: BarData = bars[0]

        if bar.interval == Interval.DAILY:
            file_path: Path = self.daily_path.joinpath(f"{bar.vt_symbol}.parquet")
        elif bar.interval == Interval.MINUTE:
            file_path = self.minute_path.joinpath(f"{bar.vt_symbol}.parquet")
        elif bar.interval:
            logger.error(f"Unsupported interval {bar.interval.value}")
            return

        def normalize_datetime(dt):
            if isinstance(dt, date) and not isinstance(dt, datetime):
                # date → datetime
                return datetime.combine(dt, datetime.min.time())
            elif isinstance(dt, datetime):
                return dt.replace(tzinfo=None)
            else:
                raise ValueError("不支持的时间类型")
        data: list = []
        for bar in bars:
            bar_data: dict = {
                "datetime": normalize_datetime(bar.datetime),
                "open": bar.open_price,
                "high": bar.high_price,
                "low": bar.low_price,
                "close": bar.close_price,
                "volume": bar.volume,
                "turnover": bar.turnover,
                "open_interest": bar.open_interest
            }
            data.append(bar_data)

        new_df: pl.DataFrame = pl.DataFrame(data)

        # If file exists, read and merge
        if file_path.exists():
            old_df: pl.DataFrame = pl.read_parquet(file_path)

            new_df = pl.concat([old_df, new_df])

            new_df = new_df.unique(subset=["datetime"])

            new_df = new_df.sort("datetime")

        # Save to file
        new_df.write_parquet(file_path)

    def load_bar_data(
        self,
        vt_symbol: str,
        interval: Interval | str,
        start: datetime | str,
        end: datetime | str
    ) -> list[BarData]:
        """
        加载K线数据

        Args:
            vt_symbol: 合约代码，如 "IF88.CFFEX"
            interval: K线周期（日线、分钟线等）
            start: 开始时间
            end: 结束时间

        Returns:
            K线数据列表

        功能：
        - 从Parquet文件读取指定时间段和周期的K线数据
        - 自动过滤时间范围内的数据
        - 转换为BarData对象返回
        """
        # Convert types
        if isinstance(interval, str):
            interval = Interval(interval)

        start = to_datetime(start)
        end = to_datetime(end)

        # Get folder path
        if interval == Interval.DAILY:
            folder_path: Path = self.daily_path
        elif interval == Interval.MINUTE:
            folder_path = self.minute_path
        else:
            logger.error(f"Unsupported interval {interval.value}")
            return []

        # Check if file exists
        file_path: Path = folder_path.joinpath(f"{vt_symbol}.parquet")
        if not file_path.exists():
            logger.error(f"File {file_path} does not exist")
            return []

        # Open file
        df: pl.DataFrame = pl.read_parquet(file_path)

        # Filter by date range
        df = df.filter((pl.col("datetime") >= start) & (pl.col("datetime") <= end))

        # Convert to BarData objects
        bars: list[BarData] = []

        symbol, exchange = extract_vt_symbol(vt_symbol)

        for row in df.iter_rows(named=True):
            bar = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=row["datetime"],
                interval=interval,
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"],
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=row["open_interest"],
                gateway_name="DB"
            )
            bars.append(bar)

        return bars

    def load_bar_df(
        self,
        vt_symbols: list[str],
        interval: Interval | str,
        start: datetime | str,
        end: datetime | str,
        extended_days: int
    ) -> pl.DataFrame | None:
        """
        加载K线数据为DataFrame格式

        Args:
            vt_symbols: 合约代码列表
            interval: K线周期
            start: 开始时间
            end: 结束时间
            extended_days: 扩展天数（用于技术指标计算）

        Returns:
            DataFrame格式的K线数据，如果无数据则返回None

        功能：
        - 批量加载多个合约的K线数据
        - 自动标准化价格（归一化到起始价格为1）
        - 处理停牌日的数据（转换为NaN）
        - 添加VWAP等衍生指标
        """
        if not vt_symbols:
            return None

        # Convert types
        if isinstance(interval, str):
            interval = Interval(interval)

        start = to_datetime(start) - timedelta(days=extended_days)
        end = to_datetime(end) + timedelta(days=extended_days // 10)

        # Get folder path
        if interval == Interval.DAILY:
            folder_path: Path = self.daily_path
        elif interval == Interval.MINUTE:
            folder_path = self.minute_path
        else:
            logger.error(f"Unsupported interval {interval.value}")
            return None

        # Read data for each symbol
        dfs: list = []

        for vt_symbol in vt_symbols:
            # Check if file exists
            file_path: Path = folder_path.joinpath(f"{vt_symbol}.parquet")
            if not file_path.exists():
                logger.error(f"File {file_path} does not exist")
                continue

            # Open file
            df: pl.DataFrame = pl.read_parquet(file_path)

            # Filter by date range
            df = df.filter((pl.col("datetime") >= start) & (pl.col("datetime") <= end))

            # Specify data types
            df = df.with_columns(
                pl.col("open"),
                pl.col("high"),
                pl.col("low"),
                pl.col("close"),
                pl.col("volume"),
                pl.col("turnover"),
                pl.col("open_interest"),
                (pl.col("turnover") / pl.col("volume")).alias("vwap")
            )

            # Check for empty data
            if df.is_empty():
                continue

            # Normalize prices
            close_0: float = df.select(pl.col("close")).item(0, 0)

            df = df.with_columns(
                (pl.col("open") / close_0).alias("open"),
                (pl.col("high") / close_0).alias("high"),
                (pl.col("low") / close_0).alias("low"),
                (pl.col("close") / close_0).alias("close"),
            )

            # Convert zeros to NaN for suspended trading days
            numeric_columns: list = df.columns[1:]                              # Extract numeric columns

            mask: pl.Series = df[numeric_columns].sum_horizontal() == 0         # Sum by row, if 0 then suspended

            df = df.with_columns(                                               # Convert suspended day values to NaN
                [pl.when(mask).then(float("nan")).otherwise(pl.col(col)).alias(col) for col in numeric_columns]
            )

            # Add symbol column
            df = df.with_columns(pl.lit(vt_symbol).alias("vt_symbol"))

            # Cache in list
            dfs.append(df)

        # Concatenate results
        result_df: pl.DataFrame = pl.concat(dfs)
        return result_df

    def save_component_data(
        self,
        index_symbol: str,
        index_components: dict[str, list[str]]
    ) -> None:
        """
        保存指数成分股数据

        Args:
            index_symbol: 指数代码，如 "000300.SH"
            index_components: 成分股字典 {日期: [成分股列表]}

        功能：
        - 使用shelve数据库保存指数每日成分股
        - 支持长期成分股历史数据管理
        """
        file_path: Path = self.component_path.joinpath(f"{index_symbol}")

        with shelve.open(str(file_path)) as db:
            db.update(index_components)

    @lru_cache      # noqa
    def load_component_data(
        self,
        index_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> dict[datetime, list[str]]:
        """
        加载指数成分股数据（带缓存）

        Args:
            index_symbol: 指数代码
            start: 开始时间
            end: 结束时间

        Returns:
            日期到成分股列表的映射字典

        功能：
        - 从shelve数据库读取指定时间范围内的成分股数据
        - 使用LRU缓存提高重复查询性能
        - 自动过滤时间范围外的数据
        """
        file_path: Path = self.component_path.joinpath(f"{index_symbol}")

        start = to_datetime(start)
        end = to_datetime(end)

        with shelve.open(str(file_path)) as db:
            keys: list[str] = list(db.keys())
            keys.sort()

            index_components: dict[datetime, list[str]] = {}
            for key in keys:
                dt: datetime = datetime.strptime(key, "%Y-%m-%d")
                if start <= dt <= end:
                    index_components[dt] = db[key]

            return index_components

    def load_component_symbols(
        self,
        index_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> list[str]:
        """
        收集指数成分股符号

        Args:
            index_symbol: 指数代码
            start: 开始时间
            end: 结束时间

        Returns:
            所有出现过的成分股代码列表（去重）

        功能：
        - 获取指定时间段内所有出现过的成分股
        - 自动去重，返回唯一成分股列表
        """
        index_components: dict[datetime, list[str]] = self.load_component_data(
            index_symbol,
            start,
            end
        )

        component_symbols: set[str] = set()

        for vt_symbols in index_components.values():
            component_symbols.update(vt_symbols)

        return list(component_symbols)

    def load_component_filters(
        self,
        index_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> dict[str, list[tuple[datetime, datetime]]]:
        """
        收集指数成分股持有期过滤器

        Args:
            index_symbol: 指数代码
            start: 开始时间
            end: 结束时间

        Returns:
            各成分股在指数中的连续持有期列表 {合约: [(开始日期, 结束日期), ...]}

        功能：
        - 分析每个成分股在指数中的连续持有时间段
        - 用于计算持股周期相关的因子
        - 支持多段持有期的处理
        """
        index_components: dict[datetime, list[str]] = self.load_component_data(
            index_symbol,
            start,
            end
        )

        # Get all trading dates and sort
        trading_dates: list[datetime] = sorted(index_components.keys())

        # Initialize component duration dictionary
        component_filters: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)

        # Get all component symbols
        all_symbols: set[str] = set()
        for vt_symbols in index_components.values():
            all_symbols.update(vt_symbols)

        # Iterate through each component to identify its duration in the index
        for vt_symbol in all_symbols:
            period_start: datetime | None = None
            period_end: datetime | None = None

            # Iterate through each trading day to identify continuous holding periods
            for trading_date in trading_dates:
                if vt_symbol in index_components[trading_date]:
                    if period_start is None:
                        period_start = trading_date

                    period_end = trading_date
                else:
                    if period_start and period_end:
                        component_filters[vt_symbol].append((period_start, period_end))
                        period_start = None
                        period_end = None

            # Handle the last holding period
            if period_start and period_end:
                component_filters[vt_symbol].append((period_start, period_end))

        return component_filters

    def add_contract_setting(
        self,
        vt_symbol: str,
        long_rate: float,
        short_rate: float,
        size: float,
        pricetick: float
    ) -> None:
        """
        添加合约交易设置信息

        Args:
            vt_symbol: 合约代码
            long_rate: 多头手续费率
            short_rate: 空头手续费率
            size: 合约乘数
            pricetick: 最小价格变动价位

        功能：
        - 保存合约的交易参数到JSON文件
        - 支持后续回测和策略执行使用
        """
        contracts: dict = {}

        if self.contract_path.exists():
            with open(self.contract_path, encoding="UTF-8") as f:
                contracts = json.load(f)

        contracts[vt_symbol] = {
            "long_rate": long_rate,
            "short_rate": short_rate,
            "size": size,
            "pricetick": pricetick
        }

        with open(self.contract_path, mode="w+", encoding="UTF-8") as f:
            json.dump(
                contracts,
                f,
                indent=4,
                ensure_ascii=False
            )

    def load_contract_setttings(self) -> dict:
        """
        加载合约交易设置

        Returns:
            合约设置字典 {合约代码: 设置信息}

        功能：
        - 从JSON文件读取所有合约的交易参数
        - 用于回测引擎和策略的参数配置
        """
        contracts: dict = {}

        if self.contract_path.exists():
            with open(self.contract_path, encoding="UTF-8") as f:
                contracts = json.load(f)

        return contracts

    def save_dataset(self, name: str, dataset: AlphaDataset) -> None:
        """
        保存数据集

        Args:
            name: 数据集名称
            dataset: AlphaDataset对象

        功能：
        - 使用pickle序列化保存因子数据集
        - 支持复杂数据结构的持久化存储
        """
        file_path: Path = self.dataset_path.joinpath(f"{name}.pkl")

        with open(file_path, mode="wb") as f:
            pickle.dump(dataset, f)

    def load_dataset(self, name: str) -> AlphaDataset | None:
        """
        加载数据集

        Args:
            name: 数据集名称

        Returns:
            AlphaDataset对象，如果文件不存在则返回None

        功能：
        - 从pickle文件恢复因子数据集
        - 支持快速加载预处理好的数据
        """
        file_path: Path = self.dataset_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Dataset file {name} does not exist")
            return None

        with open(file_path, mode="rb") as f:
            dataset: AlphaDataset = pickle.load(f)
            return dataset

    def remove_dataset(self, name: str) -> bool:
        """
        删除数据集

        Args:
            name: 数据集名称

        Returns:
            删除成功返回True，文件不存在返回False

        功能：
        - 删除指定的因子数据集文件
        - 支持清理不需要的历史数据
        """
        file_path: Path = self.dataset_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Dataset file {name} does not exist")
            return False

        file_path.unlink()
        return True

    def list_all_datasets(self) -> list[str]:
        """
        列出所有数据集

        Returns:
            所有数据集名称列表

        功能：
        - 获取当前保存的所有因子数据集名称
        - 用于管理和选择可用数据
        """
        return [file.stem for file in self.dataset_path.glob("*.pkl")]

    def save_model(self, name: str, model: AlphaModel) -> None:
        """
        保存模型

        Args:
            name: 模型名称
            model: AlphaModel对象

        功能：
        - 使用pickle序列化保存机器学习模型
        - 支持模型参数的持久化存储
        """
        file_path: Path = self.model_path.joinpath(f"{name}.pkl")

        with open(file_path, mode="wb") as f:
            pickle.dump(model, f)

    def load_model(self, name: str) -> AlphaModel | None:
        """
        加载模型

        Args:
            name: 模型名称

        Returns:
            AlphaModel对象，如果文件不存在则返回None

        功能：
        - 从pickle文件恢复机器学习模型
        - 支持快速加载训练好的模型
        """
        file_path: Path = self.model_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Model file {name} does not exist")
            return None

        with open(file_path, mode="rb") as f:
            model: AlphaModel = pickle.load(f)
            return model

    def remove_model(self, name: str) -> bool:
        """
        删除模型

        Args:
            name: 模型名称

        Returns:
            删除成功返回True，文件不存在返回False

        功能：
        - 删除指定的机器学习模型文件
        - 支持清理不需要的模型版本
        """
        file_path: Path = self.model_path.joinpath(f"{name}.pkl")
        if not file_path.exists():
            logger.error(f"Model file {name} does not exist")
            return False

        file_path.unlink()
        return True

    def list_all_models(self) -> list[str]:
        """
        列出所有模型

        Returns:
            所有模型名称列表

        功能：
        - 获取当前保存的所有机器学习模型名称
        - 用于管理和选择可用模型
        """
        return [file.stem for file in self.model_path.glob("*.pkl")]

    def save_signal(self, name: str, signal: pl.DataFrame) -> None:
        """
        保存信号

        Args:
            name: 信号名称
            signal: 信号DataFrame

        功能：
        - 使用Parquet格式保存模型预测信号
        - 支持高效存储和读取大量信号数据
        """
        file_path: Path = self.signal_path.joinpath(f"{name}.parquet")

        signal.write_parquet(file_path)

    def load_signal(self, name: str) -> pl.DataFrame | None:
        """
        加载信号

        Args:
            name: 信号名称

        Returns:
            信号DataFrame，如果文件不存在则返回None

        功能：
        - 从Parquet文件读取模型预测信号
        - 支持快速加载大量信号数据
        """
        file_path: Path = self.signal_path.joinpath(f"{name}.parquet")
        if not file_path.exists():
            logger.error(f"Signal file {name} does not exist")
            return None

        return pl.read_parquet(file_path)

    def remove_signal(self, name: str) -> bool:
        """
        删除信号

        Args:
            name: 信号名称

        Returns:
            删除成功返回True，文件不存在返回False

        功能：
        - 删除指定的模型预测信号文件
        - 支持清理不需要的信号版本
        """
        file_path: Path = self.signal_path.joinpath(f"{name}.parquet")
        if not file_path.exists():
            logger.error(f"Signal file {name} does not exist")
            return False

        file_path.unlink()
        return True

    def list_all_signals(self) -> list[str]:
        """
        列出所有信号

        Returns:
            所有信号名称列表

        功能：
        - 获取当前保存的所有模型预测信号名称
        - 用于管理和选择可用信号
        """
        return [file.stem for file in self.model_path.glob("*.parquet")]

    def save_bollinger_data(self, vt_symbol: str, bb_data: pl.DataFrame) -> None:
        """
        保存布林带数据

        Args:
            vt_symbol: 合约代码，如 "IF88.CFFEX"
            bb_data: 布林带DataFrame，必须包含datetime、upper_band、middle_band、lower_band列

        功能：
        - 使用Parquet格式保存布林带指标数据
        - 支持数据去重和追加写入
        - 与现有数据存储系统集成
        """
        if bb_data.is_empty():
            logger.warning(f"No Bollinger Bands data to save for {vt_symbol}")
            return

        # Validate required columns
        required_columns = ["datetime", "upper_band", "middle_band", "lower_band"]
        missing_columns = [col for col in required_columns if col not in bb_data.columns]
        if missing_columns:
            raise ValueError(f"Bollinger Bands DataFrame must contain columns: {required_columns}. Missing: {missing_columns}")

        # Create bollinger path if it doesn't exist
        bollinger_path: Path = self.lab_path.joinpath("bollinger")
        if not bollinger_path.exists():
            bollinger_path.mkdir(parents=True)

        file_path: Path = bollinger_path.joinpath(f"{vt_symbol}.parquet")

        # If file exists, read and merge
        if file_path.exists():
            old_df: pl.DataFrame = pl.read_parquet(file_path)

            # Concatenate new data
            new_df: pl.DataFrame = pl.concat([old_df, bb_data])

            # Remove duplicates based on datetime
            new_df = new_df.unique(subset=["datetime"])

            # Sort by datetime
            new_df = new_df.sort("datetime")

        else:
            new_df = bb_data

        # Save to file
        new_df.write_parquet(file_path)
        logger.info(f"Saved Bollinger Bands data for {vt_symbol}")

    def load_bollinger_data(
        self,
        vt_symbol: str,
        start: datetime | str,
        end: datetime | str
    ) -> pl.DataFrame | None:
        """
        加载布林带数据

        Args:
            vt_symbol: 合约代码，如 "IF88.CFFEX"
            start: 开始时间
            end: 结束时间

        Returns:
            布林带DataFrame，如果文件不存在则返回None

        功能：
        - 从Parquet文件读取指定时间段内的布林带数据
        - 自动过滤时间范围内的数据
        - 返回包含datetime、upper_band、middle_band、lower_band列的DataFrame
        """
        # Convert types
        start = to_datetime(start)
        end = to_datetime(end)

        # Get bollinger path
        bollinger_path: Path = self.lab_path.joinpath("bollinger")

        # Check if file exists
        file_path: Path = bollinger_path.joinpath(f"{vt_symbol}.parquet")
        if not file_path.exists():
            logger.error(f"Bollinger Bands file {file_path} does not exist")
            return None

        # Open file
        df: pl.DataFrame = pl.read_parquet(file_path)

        # Filter by date range
        df = df.filter((pl.col("datetime") >= start) & (pl.col("datetime") <= end))

        if df.is_empty():
            logger.warning(f"No Bollinger Bands data found for {vt_symbol} in date range {start} to {end}")
            return None

        return df

    def list_all_bollinger_signals(self) -> list[str]:
        """
        列出所有布林带信号

        Returns:
            所有布林带信号名称列表

        功能：
        - 获取当前保存的所有布林带指标数据名称
        - 用于管理和选择可用技术指标数据
        """
        bollinger_path: Path = self.lab_path.joinpath("bollinger")
        if not bollinger_path.exists():
            return []

        return [file.stem for file in bollinger_path.glob("*.parquet")]
