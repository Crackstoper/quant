"""
技术指标算子
"""

import talib
import polars as pl
import pandas as pd

from .utility import DataProxy


def to_pd_series(feature: DataProxy) -> pd.Series:
    """转换为pandas.Series数据结构"""
    series: pd.Series = feature.df.to_pandas().set_index(["datetime", "vt_symbol"])["data"]
    return series


def to_pl_dataframe(series: pd.Series) -> pl.DataFrame:
    """转换为polars.DataFrame数据结构"""
    return pl.from_pandas(series.reset_index().rename(columns={0: "data"}))


def ta_rsi(close: DataProxy, window: int) -> DataProxy:
    """按合约计算RSI指标"""
    close_: pd.Series = to_pd_series(close)

    result: pd.Series = talib.RSI(close_, timeperiod=window)   # type: ignore

    df: pl.DataFrame = to_pl_dataframe(result)
    return DataProxy(df)


def ta_atr(high: DataProxy, low: DataProxy, close: DataProxy, window: int) -> DataProxy:
    """按合约计算ATR指标"""
    high_: pd.Series = to_pd_series(high)
    low_: pd.Series = to_pd_series(low)
    close_: pd.Series = to_pd_series(close)

    result: pd.Series = talib.ATR(high_, low_, close_, timeperiod=window)   # type: ignore

    df: pl.DataFrame = to_pl_dataframe(result)
    return DataProxy(df)
