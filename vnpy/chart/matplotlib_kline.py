#!/usr/bin/env python3
"""
Matplotlib K线图绘制工具

这是一个基于matplotlib的K线图实现，提供了专业的股票价格图表功能。
支持多种技术指标、实时更新和交互式操作。

特别支持VeighNa框架的BarData对象直接输入。

Author: Claude Code
Date: 2026-03-18
"""

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MonthLocator, DayLocator, HourLocator, MinuteLocator
from matplotlib.ticker import FuncFormatter
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd
from matplotlib import font_manager
from vnpy.trader.object import BarData


available_fonts = [f.name for f in font_manager.fontManager.ttflist]
chinese_fonts = ['SimHei', 'Microsoft YaHei', 'STHeiti', 'PingFang SC']
for font in chinese_fonts:

    if font in available_fonts:
        print(f"✅ 找到中文字体: {font}")
        plt.rcParams['font.sans-serif'] = [font] + plt.rcParams.get('font.sans-serif', [])

        break


class MatplotlibKLine:
    """
    Matplotlib K线图绘制类

    功能特性：
    - 专业的蜡烛图(K线)显示
    - 成交量柱状图
    - 技术指标（移动平均线、布林带等）
    - 实时数据更新
    - 交互式操作
    - 多种时间周期支持
    """

    def __init__(self, figsize=(15, 10), dpi=100):
        """初始化K线图"""
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=figsize, dpi=dpi,
                                                     gridspec_kw={'height_ratios': [3, 1]})
        self.fig.suptitle('K线图', fontsize=16)

        # 数据存储
        self.data = {
            'datetime': [],
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        }

        # 技术指标数据
        self.indicators = {}

        # 当前显示的数据范围
        self.start_idx = 0
        self.end_idx = 0

        # 配置图表样式
        self._setup_style()

        # 交互控制
        self.is_paused = False
        self.animation_running = False

        # 连接事件
        self.fig.canvas.mpl_connect('key_press_event', self._on_key_press)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)

    def _setup_style(self):
        """设置图表样式"""

        # 颜色配置
        self.colors = {
            'up_candle': 'red',     # 上涨蜡烛橙色
            'down_candle': 'green',   # 下跌蜡烛绿色
            'ma5': '#2196f3',           # 5日均线蓝色
            'ma10': '#9c27b0',          # 10日均线紫色
            'ma20': '#f44336',          # 20日均线红色
            'boll_upper': '#ff5722',    # 布林带上轨
            'boll_lower': '#009688',    # 布林带下轨
            'volume_up': 'red',     # 上涨成交量黄色
            'volume_down': 'green'    # 下跌成交量棕色
        }

        # 设置背景色
        self.fig.patch.set_facecolor('#ffffff')
        self.ax1.patch.set_facecolor('black')
        self.ax2.patch.set_facecolor('black')



    def add_data(self, data_source: Union[List[BarData], List[dict], Tuple[List[datetime], List[float], List[float], List[float], List[float], List[int]]]):
        """添加数据（支持多种格式）"""
        if isinstance(data_source, list) and len(data_source) > 0:
            # 检查第一个元素是否是BarData对象
            if hasattr(data_source[0], 'open_price'):
                # BarData对象列表
                self._add_bar_data_objects(data_source)
            elif isinstance(data_source[0], dict):
                # 字典列表
                self._add_dict_data(data_source)
            else:
                raise ValueError("不支持的数据格式")
        elif isinstance(data_source, tuple) and len(data_source) == 6:
            # 元组格式 (datetime, open, high, low, close, volume)
            datetime_list, open_prices, high_prices, low_prices, close_prices, volumes = data_source
            self._add_raw_data(datetime_list, open_prices, high_prices, low_prices, close_prices, volumes)
        else:
            raise ValueError("不支持的数据格式")

    def _add_bar_data_objects(self, bar_data_list: List[BarData]):
        """从BarData对象列表添加数据"""
        for bar in bar_data_list:
            self.data['datetime'].append(bar.datetime)
            self.data['open'].append(float(bar.open_price))
            self.data['high'].append(float(bar.high_price))
            self.data['low'].append(float(bar.low_price))
            self.data['close'].append(float(bar.close_price))
            self.data['volume'].append(int(bar.volume))

    def _add_dict_data(self, dict_list: List[dict]):
        """从字典列表添加数据"""
        for item in dict_list:
            self.data['datetime'].append(item['datetime'])
            self.data['open'].append(float(item['open']))
            self.data['high'].append(float(item['high']))
            self.data['low'].append(float(item['low']))
            self.data['close'].append(float(item['close']))
            self.data['volume'].append(int(item['volume']))

    def _add_raw_data(self, datetime_list: List[datetime], open_prices: List[float],
                     high_prices: List[float], low_prices: List[float],
                     close_prices: List[float], volumes: List[int]):
        """从原始数据添加"""
        self.data['datetime'].extend(datetime_list)
        self.data['open'].extend(open_prices)
        self.data['high'].extend(high_prices)
        self.data['low'].extend(low_prices)
        self.data['close'].extend(close_prices)
        self.data['volume'].extend(volumes)

        # 更新索引
        if not self.end_idx:
            self.end_idx = len(self.data['datetime'])

    def calculate_moving_average(self, prices: List[float], window: int) -> List[Optional[float]]:
        """计算移动平均线"""
        ma_values = []
        for i in range(len(prices)):
            if i < window - 1:
                ma_values.append(None)
            else:
                ma = sum(prices[i-window+1:i+1]) / window
                ma_values.append(round(ma, 2))
        return ma_values

    def calculate_bollinger_bands(self, prices: List[float], window: int = 20, std_dev: float = 2) -> Dict[str, List[Optional[float]]]:
        """计算布林带指标"""
        upper_band = []
        lower_band = []

        for i in range(len(prices)):
            if i < window - 1:
                upper_band.append(None)
                lower_band.append(None)
            else:
                subset = prices[i-window+1:i+1]
                mean = sum(subset) / len(subset)
                variance = sum((x - mean) ** 2 for x in subset) / len(subset)
                std = variance ** 0.5

                upper_band.append(round(mean + std_dev * std, 2))
                lower_band.append(round(mean - std_dev * std, 2))

        return {
            'upper': upper_band,
            'middle': self.calculate_moving_average(prices, window),
            'lower': lower_band,
        }


    def _on_key_press(self, event):
        """键盘事件处理"""
        if hasattr(event, 'key') and event.key == 'right':
            # 向右移动视图
            step = 20
            self.start_idx = min(self.start_idx + step, len(self.data['datetime']) - 50)
            self.end_idx = min(self.end_idx + step, len(self.data['datetime']))
            self.plot_candlestick(self.start_idx, self.end_idx)

        elif hasattr(event, 'key') and event.key == 'left':
            # 向左移动视图
            step = 20
            self.start_idx = max(self.start_idx - step, 0)
            self.end_idx = max(self.end_idx - step, 50)
            self.plot_candlestick(self.start_idx, self.end_idx)

        elif hasattr(event, 'key') and event.key == '+':
            # 放大
            self.plot_candlestick(max(0, self.start_idx - 10), min(len(self.data['datetime']), self.end_idx + 10))

        elif hasattr(event, 'key') and event.key == '-':
            # 缩小
            self.plot_candlestick(max(0, self.start_idx - 10), min(len(self.data['datetime']), self.end_idx + 10))

    def _on_scroll(self, event):
        """鼠标滚动事件处理"""
        if hasattr(event, 'inaxes') and (event.inaxes == self.ax1 or event.inaxes == self.ax2):
            # 滚轮缩放
            base_scale = 1.2
            scale_factor = base_scale if hasattr(event, 'step') and event.step > 0 else 1/base_scale

            # 计算新的显示范围
            total_length = len(self.data['datetime'])
            current_range = self.end_idx - self.start_idx
            new_range = int(current_range * scale_factor)

            # 限制范围
            new_range = max(50, min(new_range, total_length))

            # 保持中心点不变
            center_idx = (self.start_idx + self.end_idx) // 2
            half_range = new_range // 2

            self.start_idx = max(0, center_idx - half_range)
            self.end_idx = min(total_length, center_idx + half_range + new_range % 2)

            self.plot_candlestick(self.start_idx, self.end_idx)

    def show(self):
        """显示图表"""
        plt.show()

    def save_plot(self, filename: str):
        """保存图表到文件"""
        self.fig.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"图表已保存到 {filename}")

    def _convert_to_index(self, param, default_val):
        """将datetime对象转换为索引，或保持整数"""
        if param is None:
            return default_val
        elif isinstance(param, datetime):
            # 查找最接近的datetime在数据中的位置
            for i, dt in enumerate(self.data['datetime']):
                if dt >= param:
                    return i
            return len(self.data['datetime'])  # 如果没找到，返回末尾
        else:
            return int(param)

    def plot_stick(self, start_idx=None, end_idx=None, type="candle", period="daily"):
        """绘制蜡烛图

        参数:
            start_idx: 起始位置，可以是整数索引或datetime对象
            end_idx: 结束位置，可以是整数索引或datetime对象
        """
        # 检查是否有数据
        if not self.data['datetime']:
            print("警告: 没有数据可供绘制")
            return

        start_idx = self._convert_to_index(start_idx, max(0, len(self.data['datetime']) - 100))
        end_idx = self._convert_to_index(end_idx, len(self.data['datetime']))

        # 确保索引在有效范围内
        start_idx = max(0, min(start_idx, len(self.data['datetime'])))
        end_idx = max(start_idx + 1, min(end_idx, len(self.data['datetime'])))

        self.start_idx = start_idx
        self.end_idx = end_idx

        # 清理之前的绘图
        self.ax1.clear()
        self.ax2.clear()

        # 获取当前显示的数据
        dates = self.data['datetime'][start_idx:end_idx]
        opens = self.data['open'][start_idx:end_idx]
        highs = self.data['high'][start_idx:end_idx]
        lows = self.data['low'][start_idx:end_idx]
        closes = self.data['close'][start_idx:end_idx]
        volumes = self.data['volume'][start_idx:end_idx]



        # 转换日期为matplotlib格式
        date_nums = [d.timestamp() for d in dates]

        # 绘制蜡烛图
        width = 0.6
        width2 = 0.05

        # 找出上涨和下跌的蜡烛
        up_mask = [closes[i] >= opens[i] for i in range(len(closes))]
        down_mask = [not up_mask[i] for i in range(len(closes))]

        # 绘制影线（所有K线的上下影线）
        for i, (date, high, low) in enumerate(zip(date_nums, highs, lows)):
            self.ax1.plot([date, date], [high, low], 'k-', linewidth=1)

        # 绘制实体（上涨和下跌分开处理）
        if type == 'candle':
            for i, (date, open_price, close_price) in enumerate(zip(date_nums, opens, closes)):
                color = self.colors['up_candle'] if close_price >= open_price else self.colors['down_candle']
                height = abs(close_price - open_price)
                y_pos = min(open_price, close_price)
                if type == 'candle':
                    self.ax1.add_patch(plt.Rectangle(
                        (date - width2, y_pos), width, height,
                        facecolor=color, edgecolor=color, linewidth=1
                    ))
        elif type == 'line':
            self.ax1.plot(dates, highs, linestyle='-',color='red')
            self.ax1.plot(dates, lows, linestyle='-', color='green')
            self.ax1.plot(dates, opens, linestyle='-', color='red')
            self.ax1.plot(dates, closes, linestyle='-', color='green')

        # 绘制成交量图
        volume_dates = date_nums
        volume_colors = [self.colors['volume_up'] if closes[i] >= opens[i] else self.colors['volume_down']
                        for i in range(len(closes))]

        self.ax2.bar(volume_dates, volumes, width=width*0.8, color=volume_colors, alpha=0.7)

        # 设置坐标轴标签和标题（中文）
        self.ax1.set_title('K线图 - 专业股票分析', fontsize=14, fontweight='bold')
        self.ax1.set_ylabel('价格 (元)', fontsize=12)

        self.ax2.set_title('成交量分析', fontsize=12)
        self.ax2.set_ylabel('成交量 (手)', fontsize=10)
        self.ax2.set_xlabel('时间', fontsize=12)

        # 设置X轴范围
        if date_nums and len(date_nums) > 1:
            self.ax1.set_xlim(min(date_nums), max(date_nums))
            self.ax2.set_xlim(min(date_nums), max(date_nums))

        # 自动调整布局
        self.fig.tight_layout()

        # 刷新显示
        if hasattr(self.fig, 'canvas'):
            self.fig.canvas.draw_idle()
