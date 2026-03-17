"""
AKShare数据库后端实现

基于AKShare的数据存储和检索实现，提供VeighNa框架的数据持久化功能。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import pandas as pd

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData
from vnpy.trader.database import BaseDatabase, BarOverview, TickOverview, convert_tz
from vnpy.trader.setting import SETTINGS


class AkshareDatabase(BaseDatabase):
    """
    AKShare数据库后端实现

    使用文件系统存储AKShare获取的数据，提供标准VeighNa数据访问接口。
    """

    def __init__(self) -> None:
        """初始化数据库连接"""
        self.db_folder: str = SETTINGS["database.path"]
        if not self.db_folder:
            self.db_folder = "data"

        # 创建数据目录
        self.data_path = Path(self.db_folder)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        self.bar_path = self.data_path / "bars"
        self.tick_path = self.data_path / "ticks"
        self.overview_path = self.data_path / "overviews"

        for path in [self.bar_path, self.tick_path, self.overview_path]:
            path.mkdir(exist_ok=True)

    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        """
        保存K线数据到数据库

        Args:
            bars: BarData对象列表
            stream: 是否为流式数据（追加模式）

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            if not bars:
                return True

            # 获取符号信息
            symbol = bars[0].symbol
            exchange = bars[0].exchange.value
            interval = bars[0].interval.value if bars[0].interval else "unknown"

            # 生成文件名
            filename = f"{symbol}_{exchange}_{interval}.json"
            filepath = self.bar_path / filename

            # 读取现有数据（如果不是流式）
            existing_bars = []
            if not stream and filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    for bar_dict in existing_data:
                        existing_bars.append(BarData(**bar_dict))

            # 合并数据并去重
            all_bars = existing_bars + bars
            unique_bars = self._remove_duplicates(all_bars)

            # 按时间排序
            unique_bars.sort(key=lambda x: x.datetime)

            # 保存到文件
            bar_dicts = []
            for bar in unique_bars:
                bar_dict = {
                    "symbol": bar.symbol,
                    "exchange": bar.exchange.value,
                    "datetime": bar.datetime.isoformat() if bar.datetime else None,
                    "interval": bar.interval.value if bar.interval else None,
                    "volume": bar.volume,
                    "turnover": bar.turnover,
                    "open_interest": bar.open_interest,
                    "open_price": bar.open_price,
                    "high_price": bar.high_price,
                    "low_price": bar.low_price,
                    "close_price": bar.close_price,
                    "gateway_name": bar.gateway_name
                }
                bar_dicts.append(bar_dict)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(bar_dicts, f, ensure_ascii=False, indent=2)

            # 更新概览信息
            self._update_bar_overview(symbol, exchange, interval, unique_bars)

            print(f"保存K线数据成功: {len(unique_bars)}条记录 -> {filepath}")
            return True

        except Exception as e:
            print(f"保存K线数据失败: {e}")
            return False

    def save_tick_data(self, ticks: List[TickData], stream: bool = False) -> bool:
        """
        保存Tick数据到数据库

        Args:
            ticks: TickData对象列表
            stream: 是否为流式数据（追加模式）

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            if not ticks:
                return True

            # 获取符号信息
            symbol = ticks[0].symbol
            exchange = ticks[0].exchange.value

            # 生成文件名
            filename = f"{symbol}_{exchange}_tick.json"
            filepath = self.tick_path / filename

            # 读取现有数据（如果不是流式）
            existing_ticks = []
            if not stream and filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    for tick_dict in existing_data:
                        existing_ticks.append(TickData(**tick_dict))

            # 合并数据并去重
            all_ticks = existing_ticks + ticks
            unique_ticks = self._remove_ticks_duplicates(all_ticks)

            # 按时间排序
            unique_ticks.sort(key=lambda x: x.datetime or datetime.now())

            # 保存到文件
            tick_dicts = []
            for tick in unique_ticks:
                tick_dict = {
                    "symbol": tick.symbol,
                    "exchange": tick.exchange.value,
                    "datetime": tick.datetime.isoformat() if tick.datetime else None,
                    "name": tick.name,
                    "volume": tick.volume,
                    "turnover": tick.turnover,
                    "open_interest": tick.open_interest,
                    "last_price": tick.last_price,
                    "last_volume": tick.last_volume,
                    "limit_up": tick.limit_up,
                    "limit_down": tick.limit_down,
                    "open_price": tick.open_price,
                    "high_price": tick.high_price,
                    "low_price": tick.low_price,
                    "pre_close": tick.pre_close,
                    "bid_price_1": tick.bid_price_1,
                    "bid_price_2": tick.bid_price_2,
                    "bid_price_3": tick.bid_price_3,
                    "bid_price_4": tick.bid_price_4,
                    "bid_price_5": tick.bid_price_5,
                    "ask_price_1": tick.ask_price_1,
                    "ask_price_2": tick.ask_price_2,
                    "ask_price_3": tick.ask_price_3,
                    "ask_price_4": tick.ask_price_4,
                    "ask_price_5": tick.ask_price_5,
                    "bid_volume_1": tick.bid_volume_1,
                    "bid_volume_2": tick.bid_volume_2,
                    "bid_volume_3": tick.bid_volume_3,
                    "bid_volume_4": tick.bid_volume_4,
                    "bid_volume_5": tick.bid_volume_5,
                    "ask_volume_1": tick.ask_volume_1,
                    "ask_volume_2": tick.ask_volume_2,
                    "ask_volume_3": tick.ask_volume_3,
                    "ask_volume_4": tick.ask_volume_4,
                    "ask_volume_5": tick.ask_volume_5,
                    "localtime": tick.localtime.isoformat() if tick.localtime else None,
                    "gateway_name": tick.gateway_name
                }
                tick_dicts.append(tick_dict)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tick_dicts, f, ensure_ascii=False, indent=2)

            # 更新概览信息
            self._update_tick_overview(symbol, exchange, unique_ticks)

            print(f"保存Tick数据成功: {len(unique_ticks)}条记录 -> {filepath}")
            return True

        except Exception as e:
            print(f"保存Tick数据失败: {e}")
            return False

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> List[BarData]:
        """
        从数据库加载K线数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期
            start: 开始时间
            end: 结束时间

        Returns:
            List[BarData]: K线数据列表
        """
        try:
            # 生成文件名
            filename = f"{symbol}_{exchange.value}_{interval.value}.json"
            filepath = self.bar_path / filename

            if not filepath.exists():
                print(f"K线数据文件不存在: {filepath}")
                return []

            # 读取数据
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 转换为BarData对象
            bars = []
            for bar_dict in data:
                # 转换日期格式
                if bar_dict.get("datetime"):
                    bar_dict["datetime"] = datetime.fromisoformat(bar_dict["datetime"])
                if bar_dict.get("interval") and bar_dict["interval"]:
                    bar_dict["interval"] = Interval(bar_dict["interval"])

                bar = BarData(**bar_dict)
                bars.append(bar)

            # 过滤时间范围
            filtered_bars = [
                bar for bar in bars
                if start <= bar.datetime <= end
            ]

            print(f"加载K线数据成功: {len(filtered_bars)}条记录")
            return filtered_bars

        except Exception as e:
            print(f"加载K线数据失败: {e}")
            return []

    def load_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> List[TickData]:
        """
        从数据库加载Tick数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            start: 开始时间
            end: 结束时间

        Returns:
            List[TickData]: Tick数据列表
        """
        try:
            # 生成文件名
            filename = f"{symbol}_{exchange.value}_tick.json"
            filepath = self.tick_path / filename

            if not filepath.exists():
                print(f"Tick数据文件不存在: {filepath}")
                return []

            # 读取数据
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 转换为TickData对象
            ticks = []
            for tick_dict in data:
                # 转换日期格式
                if tick_dict.get("datetime"):
                    tick_dict["datetime"] = datetime.fromisoformat(tick_dict["datetime"])
                if tick_dict.get("localtime"):
                    tick_dict["localtime"] = datetime.fromisoformat(tick_dict["localtime"])

                tick = TickData(**tick_dict)
                ticks.append(tick)

            # 过滤时间范围
            filtered_ticks = [
                tick for tick in ticks
                if start <= (tick.datetime or datetime.now()) <= end
            ]

            print(f"加载Tick数据成功: {len(filtered_ticks)}条记录")
            return filtered_ticks

        except Exception as e:
            print(f"加载Tick数据失败: {e}")
            return []

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """
        删除指定符号的K线数据

        Args:
            symbol: 股票代码
            exchange: 交易所
            interval: K线周期

        Returns:
            int: 删除的记录数
        """
        try:
            filename = f"{symbol}_{exchange.value}_{interval.value}.json"
            filepath = self.bar_path / filename

            if not filepath.exists():
                return 0

            # 读取现有数据
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            record_count = len(data)

            # 删除文件
            filepath.unlink()

            # 清理概览信息
            overview_file = self.overview_path / f"bar_{symbol}_{exchange.value}_{interval.value}.json"
            if overview_file.exists():
                overview_file.unlink()

            print(f"删除K线数据成功: {record_count}条记录")
            return record_count

        except Exception as e:
            print(f"删除K线数据失败: {e}")
            return 0

    def delete_tick_data(
        self,
        symbol: str,
        exchange: Exchange
    ) -> int:
        """
        删除指定符号的Tick数据

        Args:
            symbol: 股票代码
            exchange: 交易所

        Returns:
            int: 删除的记录数
        """
        try:
            filename = f"{symbol}_{exchange.value}_tick.json"
            filepath = self.tick_path / filename

            if not filepath.exists():
                return 0

            # 读取现有数据
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            record_count = len(data)

            # 删除文件
            filepath.unlink()

            # 清理概览信息
            overview_file = self.overview_path / f"tick_{symbol}_{exchange.value}.json"
            if overview_file.exists():
                overview_file.unlink()

            print(f"删除Tick数据成功: {record_count}条记录")
            return record_count

        except Exception as e:
            print(f"删除Tick数据失败: {e}")
            return 0

    def get_bar_overview(self) -> List[BarOverview]:
        """
        获取数据库中所有K线数据概览

        Returns:
            List[BarOverview]: 数据概览列表
        """
        overviews = []

        try:
            for file_path in self.bar_path.glob("*.json"):
                try:
                    filename = file_path.stem
                    parts = filename.split('_')

                    if len(parts) >= 3:
                        symbol = parts[0]
                        exchange = parts[1]
                        interval = parts[2]

                        # 读取文件获取统计信息
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        if data:
                            start_dt = datetime.fromisoformat(data[0]["datetime"]) if data[0].get("datetime") else None
                            end_dt = datetime.fromisoformat(data[-1]["datetime"]) if data[-1].get("datetime") else None

                            overview = BarOverview(
                                symbol=symbol,
                                exchange=Exchange(exchange),
                                interval=Interval(interval),
                                count=len(data),
                                start=start_dt,
                                end=end_dt
                            )
                            overviews.append(overview)

                except Exception as e:
                    print(f"处理文件 {file_path} 时出错: {e}")
                    continue

        except Exception as e:
            print(f"获取K线数据概览失败: {e}")

        return overviews

    def get_tick_overview(self) -> List[TickOverview]:
        """
        获取数据库中所有Tick数据概览

        Returns:
            List[TickOverview]: 数据概览列表
        """
        overviews = []

        try:
            for file_path in self.tick_path.glob("*.json"):
                try:
                    filename = file_path.stem
                    parts = filename.split('_')

                    if len(parts) >= 2:
                        symbol = parts[0]
                        exchange = parts[1]

                        # 读取文件获取统计信息
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        if data:
                            start_dt = datetime.fromisoformat(data[0]["datetime"]) if data[0].get("datetime") else None
                            end_dt = datetime.fromisoformat(data[-1]["datetime"]) if data[-1].get("datetime") else None

                            overview = TickOverview(
                                symbol=symbol,
                                exchange=Exchange(exchange),
                                count=len(data),
                                start=start_dt,
                                end=end_dt
                            )
                            overviews.append(overview)

                except Exception as e:
                    print(f"处理文件 {file_path} 时出错: {e}")
                    continue

        except Exception as e:
            print(f"获取Tick数据概览失败: {e}")

        return overviews

    def _remove_duplicates(self, bars: List[BarData]) -> List[BarData]:
        """移除重复的K线数据"""
        seen = set()
        unique_bars = []

        for bar in bars:
            key = (bar.symbol, bar.exchange.value, bar.datetime)
            if key not in seen:
                seen.add(key)
                unique_bars.append(bar)

        return unique_bars

    def _remove_ticks_duplicates(self, ticks: List[TickData]) -> List[TickData]:
        """移除重复的Tick数据"""
        seen = set()
        unique_ticks = []

        for tick in ticks:
            key = (tick.symbol, tick.exchange.value, tick.datetime)
            if key not in seen:
                seen.add(key)
                unique_ticks.append(tick)

        return unique_ticks

    def _update_bar_overview(self, symbol: str, exchange: str, interval: str, bars: List[BarData]) -> None:
        """更新K线数据概览"""
        try:
            overview_file = self.overview_path / f"bar_{symbol}_{exchange}_{interval}.json"

            if bars:
                start_dt = bars[0].datetime
                end_dt = bars[-1].datetime
            else:
                start_dt = None
                end_dt = None

            overview = BarOverview(
                symbol=symbol,
                exchange=Exchange(exchange),
                interval=Interval(interval),
                count=len(bars),
                start=start_dt,
                end=end_dt
            )

            overview_data = {
                "symbol": overview.symbol,
                "exchange": overview.exchange.value,
                "interval": overview.interval.value,
                "count": overview.count,
                "start": overview.start.isoformat() if overview.start else None,
                "end": overview.end.isoformat() if overview.end else None
            }

            with open(overview_file, 'w', encoding='utf-8') as f:
                json.dump(overview_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"更新K线数据概览失败: {e}")

    def _update_tick_overview(self, symbol: str, exchange: str, ticks: List[TickData]) -> None:
        """更新Tick数据概览"""
        try:
            overview_file = self.overview_path / f"tick_{symbol}_{exchange}.json"

            if ticks:
                start_dt = ticks[0].datetime
                end_dt = ticks[-1].datetime
            else:
                start_dt = None
                end_dt = None

            overview = TickOverview(
                symbol=symbol,
                exchange=Exchange(exchange),
                count=len(ticks),
                start=start_dt,
                end=end_dt
            )

            overview_data = {
                "symbol": overview.symbol,
                "exchange": overview.exchange.value,
                "count": overview.count,
                "start": overview.start.isoformat() if overview.start else None,
                "end": overview.end.isoformat() if overview.end else None
            }

            with open(overview_file, 'w', encoding='utf-8') as f:
                json.dump(overview_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"更新Tick数据概览失败: {e}")


# 注册到设置系统
def register_database() -> None:
    """注册数据库后端"""
    from vnpy.trader.setting import SETTINGS

    # 如果用户没有配置数据库路径，使用默认的AKShare数据库
    if not SETTINGS["database.engine"]:
        SETTINGS["database.engine"] = "akshare"
        SETTINGS["database.path"] = "data"

    print("AKShare数据库后端已注册")


# 自动注册
register_database()