import time
from datetime import datetime
from typing import cast
from collections.abc import Callable
from multiprocessing import get_context
from multiprocessing.context import BaseContext

import polars as pl
import pandas as pd
from tqdm import tqdm
from alphalens.utils import get_clean_factor_and_forward_returns    # type: ignore
from alphalens.tears import create_full_tear_sheet                  # type: ignore

from ..logger import logger
from .utility import (
    to_datetime,
    Segment,
    calculate_by_expression,
    calculate_by_polars
)


class AlphaDataset:
    """Alpha 数据集模板类"""

    def __init__(
        self,
        df: pl.DataFrame,
        train_period: tuple[str, str],
        valid_period: tuple[str, str],
        test_period: tuple[str, str],
        process_type: str = "append"
    ) -> None:
        """构造函数"""
        self.df: pl.DataFrame = df

        # 处理后的数据 DataFrame
        self.result_df: pl.DataFrame
        self.raw_df: pl.DataFrame
        self.infer_df: pl.DataFrame
        self.learn_df: pl.DataFrame

        # 新版本数据期间配置
        self.data_periods: dict[Segment, tuple[str, str]] = {
            Segment.TRAIN: train_period,
            Segment.VALID: valid_period,
            Segment.TEST: test_period
        }

        self.feature_expressions: dict[str, str | pl.expr.expr.Expr] = {}
        self.feature_results: dict[str, pl.DataFrame] = {}
        self.label_expression: str = ""

        self.process_type: str = process_type
        self.infer_processors: list = []
        self.learn_processors: list = []

    def add_feature(
        self,
        name: str,
        expression: str | pl.expr.expr.Expr | None = None,
        result: pl.DataFrame | None = None
    ) -> None:
        """
        添加特征表达式
        """
        if expression is not None and result is not None:
            raise ValueError("只能提供 'expression' 或 'result' 之一")

        if expression is not None:
            self.feature_expressions[name] = expression
        elif result is not None:
            self.feature_results[name] = result

    def set_label(self, expression: str) -> None:
        """
        设置标签表达式
        """
        self.label_expression = expression

    def add_processor(self, task: str, processor: Callable[[pl.DataFrame], None]) -> None:
        """
        添加特征预处理器
        """
        if task == "infer":
            self.infer_processors.append(processor)
        else:
            self.learn_processors.append(processor)

    def prepare_data(self, filters: dict | None = None, max_workers: int | None = None) -> None:
        """
        生成所需数据
        """
        # 特征数据结果列表
        results: list = []

        # 遍历表达式进行计算
        expressions: list[tuple[str, str | pl.expr.expr.Expr]] = list(self.feature_expressions.items())

        if self.label_expression:
            expressions.append(("label", self.label_expression))

        # 创建进程池
        logger.info("开始计算表达式因子特征")

        args: list[tuple] = [(self.df, name, expression) for name, expression in expressions]

        context: BaseContext = get_context("spawn")

        with context.Pool(processes=max_workers) as pool:
            # 并行计算所有表达式
            it = pool.imap(calculate_feature, args)

            # 收集结果
            for result in tqdm(it, total=len(args)):
                results.append(result)

        self.result_df = self.df.with_columns(results)

        # 合并结果数据因子特征
        logger.info("开始合并结果数据因子特征")

        label_exist: bool = "label" in self.result_df
        for name, feature_result in tqdm(self.feature_results.items()):
            feature_result = feature_result.rename({"data": name})
            self.result_df = self.result_df.join(feature_result, on=["datetime", "vt_symbol"], how="left")

        if label_exist:
            # 将标签放在最后一列
            cols: list = [col for col in self.result_df.columns if col != "label"] + ["label"]
            self.result_df = self.result_df.select(cols).sort(["datetime", "vt_symbol"])

        # 生成原始数据
        raw_df = self.result_df.fill_null(float("nan"))

        if filters:
            logger.info("开始筛选成分股数据")

            dfs: list[pl.DataFrame] = []

            for vt_symbol, ranges in tqdm(filters.items(), total=len(filters)):
                for start, end in ranges:
                    temp_df = raw_df.filter(
                        (pl.col("vt_symbol") == vt_symbol)
                        & (pl.col("datetime") >= pl.lit(start))
                        & (pl.col("datetime") <= pl.lit(end))
                    )
                    dfs.append(temp_df)

            raw_df = pl.concat(dfs)

        # 只保留特征列
        select_columns: list[str] = ["datetime", "vt_symbol"] + raw_df.columns[self.df.width:]
        self.raw_df = raw_df.select(select_columns).sort(["datetime", "vt_symbol"])

        self.infer_df = self.raw_df
        self.learn_df = self.raw_df

    def process_data(self) -> None:
        """
        处理数据
        """
        # 生成推理数据
        for processor in self.infer_processors:
            self.infer_df = processor(df=self.infer_df)

        # 生成学习数据
        if self.process_type == "append":
            self.learn_df = self.infer_df

        for processor in self.learn_processors:
            self.learn_df = processor(df=self.learn_df)

    def fetch_raw(self, segment: Segment) -> pl.DataFrame:
        """
        获取特定分段的原始数据
        """
        start, end = self.data_periods[segment]
        return query_by_time(self.raw_df, start, end)

    def fetch_infer(self, segment: Segment) -> pl.DataFrame:
        """
        获取特定分段的推理数据
        """
        start, end = self.data_periods[segment]
        return query_by_time(self.infer_df, start, end)

    def fetch_learn(self, segment: Segment) -> pl.DataFrame:
        """
        获取特定分段的学习数据
        """
        start, end = self.data_periods[segment]
        return query_by_time(self.learn_df, start, end)

    def show_feature_performance(self, name: str) -> None:
        """
        执行特征性能分析
        """
        starts: list[datetime] = []
        ends: list[datetime] = []

        for period in self.data_periods.values():
            starts.append(to_datetime(period[0]))
            ends.append(to_datetime(period[1]))

        start: datetime = min(starts)
        end: datetime = max(ends)

        # 选择时间范围
        result_df: pl.DataFrame = query_by_time(self.result_df, start, end)
        learn_df: pl.DataFrame = query_by_time(self.learn_df, start, end)

        merged_df = (
            result_df
            .select(["datetime", "vt_symbol", "close"])
            .join(
                learn_df.select(["datetime", "vt_symbol", name]),
                on=["datetime", "vt_symbol"],
                how="inner"
            )
        )

        # 填充 NaN 并删除空值
        merged_df = merged_df.fill_nan(None).drop_nulls()

        # 提取特征
        feature_df: pd.DataFrame = merged_df.select(["datetime", "vt_symbol", name]).to_pandas()
        feature_df.set_index(["datetime", "vt_symbol"], inplace=True)

        feature_s: pd.Series = feature_df[name]

        # 提取价格
        price_df: pd.DataFrame = merged_df.select(["datetime", "vt_symbol", "close"]).to_pandas()
        price_df = price_df.pivot(index="datetime", columns="vt_symbol", values="close")

        # 合并数据
        clean_data: pd.DataFrame = get_clean_factor_and_forward_returns(feature_s, price_df, quantiles=10)

        # 执行分析
        create_full_tear_sheet(clean_data)

    def show_signal_performance(self, signal: pl.DataFrame) -> None:
        """
        执行预测信号性能分析
        """
        # 获取信号开始和结束时间
        start: datetime = cast(datetime, signal["datetime"].min())
        end: datetime = cast(datetime, signal["datetime"].max())

        # 选择时间范围
        df: pl.DataFrame = query_by_time(self.result_df, start, end)

        # 提取特征
        signal_df: pd.DataFrame = signal.to_pandas()
        signal_df.set_index(["datetime", "vt_symbol"], inplace=True)
        signal_s: pd.Series = signal_df["signal"]

        # 提取价格
        price_df: pd.DataFrame = df.select(["datetime", "vt_symbol", "close"]).to_pandas()
        price_df = price_df.pivot(index="datetime", columns="vt_symbol", values="close")

        # 合并数据
        clean_data: pd.DataFrame = get_clean_factor_and_forward_returns(
            signal_s,
            price_df,
            max_loss=1.0,
            quantiles=10
        )

        # 执行分析
        create_full_tear_sheet(clean_data)


def query_by_time(df: pl.DataFrame, start: datetime | str = "", end: datetime | str = "") -> pl.DataFrame:
    """
    基于时间范围过滤 DataFrame
    """
    if start:
        start = to_datetime(start)
        df = df.filter(pl.col("datetime") >= start)

    if end:
        end = to_datetime(end)
        df = df.filter(pl.col("datetime") <= end)

    return df.sort(["datetime", "vt_symbol"])


def calculate_feature(args: tuple[pl.DataFrame, str, str | pl.expr.expr.Expr]) -> pl.Series:
    """
    通过表达式计算特征
    """
    start = time.time()

    df, name, expression = args

    if isinstance(expression, pl.expr.expr.Expr):
        result = calculate_by_polars(df, expression)["data"].alias(name)
    else:
        result = calculate_by_expression(df, expression)["data"].alias(name)

    end = time.time()
    print(f"特征计算 {name} 耗时: {end - start} 秒 | {expression}")

    return result
