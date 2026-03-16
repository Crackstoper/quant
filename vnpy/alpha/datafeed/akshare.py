"""
Akshare数据服务实现

提供通过akshare库获取股票、期货等金融数据的接口。
"""

import re
from datetime import datetime
from typing import Callable, Optional

import akshare as ak
import pandas as pd

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import BarData, HistoryRequest, TickData


class AkshareDatafeed(BaseDatafeed):
    """
    Akshare数据服务类

    通过akshare库提供股票、期货等金融数据的查询服务。
    """

    def __init__(self) -> None:
        """初始化数据服务"""
        self._output: Callable = print
        self._initialized: bool = False

    def init(self, output: Callable = print) -> bool:
        """
        初始化数据服务连接

        Args:
            output: 输出函数，用于打印日志信息

        Returns:
            bool: 是否成功初始化
        """
        self._output = output

        try:
            # 测试akshare连接
            test_df = ak.stock_zh_a_hist(
                symbol="000001",
                period="daily",
                start_date="20240101",
                end_date="20240102"
            )
            if len(test_df) > 0:
                self._initialized = True
                self._output("Akshare数据服务初始化成功")
                return True
            else:
                self._output("Akshare数据服务初始化失败：未获取到测试数据")
                return False

        except Exception as e:
            self._output(f"Akshare数据服务初始化异常: {e}")
            return False

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> list[BarData]:
        """
        查询历史K线数据

        Args:
            req: 历史数据请求对象
            output: 输出函数

        Returns:
            list[BarData]: K线数据列表
        """
        if not self._initialized:
            output("Akshare数据服务未初始化")
            return []

        try:
            # 将VT符号转换为akshare格式
            akshare_symbol, exchange_str = self._convert_vt_to_akshare_symbol(req.vt_symbol)

            # 根据交易所类型选择不同的API
            if exchange_str in ["SSE", "SZSE", "BSE"]:
                return self._query_stock_bar_history(req, akshare_symbol)
            elif exchange_str == "CFFEX":
                return self._query_futures_bar_history(req, akshare_symbol)
            else:
                output(f"不支持的交易所: {exchange_str}")
                return []

        except Exception as e:
            output(f"查询K线历史数据异常: {e}")
            return []

    def _query_stock_bar_history(self, req: HistoryRequest, symbol: str) -> list[BarData]:
        """查询股票历史K线数据"""
        try:
            # 转换日期格式
            start_date = req.start.strftime("%Y%m%d")
            end_date = req.end.strftime("%Y%m%d") if req.end else datetime.now().strftime("%Y%m%d")

            # 调用akshare API
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=self._interval_to_akshare_period(req.interval),
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                self._output(f"未获取到{req.symbol}的历史数据")
                return []

            # 转换为BarData列表
            bars = []
            for _, row in df.iterrows():
                bar = BarData(
                    symbol=req.symbol.split(".")[0],  # 移除交易所后缀
                    exchange=req.exchange,
                    datetime=row["日期"],
                    interval=req.interval,
                    open_price=float(row["开盘"]),
                    high_price=float(row["最高"]),
                    low_price=float(row["最低"]),
                    close_price=float(row["收盘"]),
                    volume=float(row["成交量"]),
                    turnover=float(row["成交额"]) if not pd.isna(row["成交额"]) else 0.0,
                    gateway_name="AKSHARE"
                )
                bars.append(bar)

            return bars

        except Exception as e:
            self._output(f"查询股票历史数据异常: {e}")
            return []

    def _query_futures_bar_history(self, req: HistoryRequest, symbol: str) -> list[BarData]:
        """查询期货历史K线数据"""
        try:
            # 注意：akshare的期货API需要特殊处理
            # 这里使用一个简单的实现，实际使用时可能需要更复杂的逻辑

            start_date = req.start.strftime("%Y%m%d")
            end_date = req.end.strftime("%Y%m%d") if req.end else datetime.now().strftime("%Y%m%d")

            # 尝试获取期货数据
            try:
                df = ak.futures_hist_em(
                    symbol=symbol,
                    period=self._interval_to_akshare_period(req.interval),
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception:
                # 如果期货API不可用，返回空列表
                self._output(f"akshare期货API暂不支持{symbol}的数据获取")
                return []

            if df.empty:
                self._output(f"未获取到期货{symbol}的历史数据")
                return []

            # 转换为BarData列表（简化版本）
            bars = []
            for _, row in df.iterrows():
                bar = BarData(
                    symbol=req.symbol.split(".")[0],
                    exchange=req.exchange,
                    datetime=row.get("datetime", datetime.now()),
                    interval=req.interval,
                    open_price=float(row.get("open", 0)),
                    high_price=float(row.get("high", 0)),
                    low_price=float(row.get("low", 0)),
                    close_price=float(row.get("close", 0)),
                    volume=float(row.get("volume", 0)),
                    turnover=float(row.get("amount", 0)),
                    gateway_name="AKSHARE"
                )
                bars.append(bar)

            return bars

        except Exception as e:
            self._output(f"查询期货历史数据异常: {e}")
            return []

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> list[TickData]:
        """
        查询历史Tick数据

        Args:
            req: 历史数据请求对象
            output: 输出函数

        Returns:
            list[TickData]: Tick数据列表
        """
        output("Akshare数据服务暂不支持Tick历史数据查询")
        return []

    def _convert_vt_to_akshare_symbol(self, vt_symbol: str) -> tuple[str, str]:
        """
        将VT符号转换为akshare符号和交易所代码

        Args:
            vt_symbol: VT格式的符号 (如 '000001.SZSE')

        Returns:
            tuple: (akshare_symbol, exchange_code)
        """
        try:
            symbol, exchange = vt_symbol.split(".")
            exchange_code = exchange.upper()

            # 映射交易所代码
            if exchange_code == "SZSE":
                # 深圳股票
                if re.match(r'^\d{6}$', symbol) and int(symbol) >= 300000:
                    return symbol, "SZSE"
            elif exchange_code == "SSE":
                # 上海股票
                if re.match(r'^\d{6}$', symbol) and int(symbol) < 300000:
                    return symbol, "SSE"
            elif exchange_code == "BSE":
                # 北京股票
                if re.match(r'^[84]\d{5}$', symbol):
                    return symbol, "BSE"

            # 对于期货和其他类型，返回原始符号
            return symbol, exchange_code

        except Exception:
            return vt_symbol, "UNKNOWN"

    def _interval_to_akshare_period(self, interval: Interval) -> str:
        """
        将VeighNa的Interval转换为akshare的period参数

        Args:
            interval: VeighNa的Interval枚举值

        Returns:
            str: akshare支持的period字符串
        """
        mapping = {
                Interval.MINUTE : "1m",
                Interval.HOUR : "1h",
                Interval.DAILY : "daily",
                Interval.WEEKLY : "weekly",
                Interval.TICK : "tick",
                Interval.MONTHLY : "monthly",
        }

        return mapping.get(interval, "daily")

    def get_supported_symbols(self, exchange: Optional[str] = None) -> list[str]:
        """
        获取支持的证券列表

        Args:
            exchange: 交易所代码，如 "SSE", "SZSE"

        Returns:
            list[str]: 支持的证券代码列表
        """
        try:
            if exchange == "SSE":
                # 获取上证股票列表
                df = ak.stock_sh_cons()
                return [str(code) for code in df["code"].tolist()]
            elif exchange == "SZSE":
                # 获取深证股票列表
                df = ak.stock_sz_cons()
                return [str(code) for code in df["code"].tolist()]
            else:
                # 默认返回一些示例股票
                return ["000001", "600000", "000002", "600036"]

        except Exception as e:
            self._output(f"获取支持证券列表异常: {e}")
            return []