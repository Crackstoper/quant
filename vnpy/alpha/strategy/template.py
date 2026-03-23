from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

import polars as pl

from vnpy.trader.object import BarData, TradeData, OrderData
from vnpy.trader.constant import Offset, Direction


if TYPE_CHECKING:
    from vnpy.alpha.strategy.backtesting import BacktestingEngine


class AlphaStrategy(metaclass=ABCMeta):
    """Alpha策略模板类"""

    def __init__(
        self,
        strategy_engine: "BacktestingEngine",
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        self.strategy_engine: BacktestingEngine = strategy_engine
        self.strategy_name: str = strategy_name
        self.vt_symbols: list[str] = vt_symbols

        # 持仓数据字典
        self.pos_data: dict[str, float] = defaultdict(float)        # 实际持仓
        self.target_data: dict[str, float] = defaultdict(float)     # 目标持仓

        # 订单缓存容器
        self.orders: dict[str, OrderData] = {}
        self.active_orderids: set[str] = set()

        # 设置策略参数
        for k, v in setting.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @abstractmethod
    def on_init(self) -> None:
        """初始化回调"""
        pass

    @abstractmethod
    def on_bars(self, bars: dict[str, BarData]) -> None:
        """K线切片回调"""
        pass

    @abstractmethod
    def on_trade(self, trade: TradeData) -> None:
        """成交回调"""
        pass

    def update_trade(self, trade: TradeData) -> None:
        """更新交易数据"""
        if trade.direction == Direction.LONG:
            self.pos_data[trade.vt_symbol] += trade.volume
        else:
            self.pos_data[trade.vt_symbol] -= trade.volume

        self.on_trade(trade)

    def update_order(self, order: OrderData) -> None:
        """更新订单数据"""
        self.orders[order.vt_orderid] = order

        if not order.is_active() and order.vt_orderid in self.active_orderids:
            self.active_orderids.remove(order.vt_orderid)

    def get_signal(self) -> pl.DataFrame:
        """获取当前信号"""
        return self.strategy_engine.get_signal()

    def buy(self, vt_symbol: str, price: float, volume: float) -> list[str]:
        """买入开仓"""
        return self.send_order(vt_symbol, Direction.LONG, Offset.OPEN, price, volume)

    def sell(self, vt_symbol: str, price: float, volume: float) -> list[str]:
        """卖出平仓"""
        return self.send_order(vt_symbol, Direction.SHORT, Offset.CLOSE, price, volume)

    def short(self, vt_symbol: str, price: float, volume: float) -> list[str]:
        """卖出开仓"""
        return self.send_order(vt_symbol, Direction.SHORT, Offset.OPEN, price, volume)

    def cover(self, vt_symbol: str, price: float, volume: float) -> list[str]:
        """买入平仓"""
        return self.send_order(vt_symbol, Direction.LONG, Offset.CLOSE, price, volume)

    def send_order(
        self,
        vt_symbol: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float
    ) -> list[str]:
        """发送订单"""
        vt_orderids: list = self.strategy_engine.send_order(
            self, vt_symbol, direction, offset, price, volume
        )

        for vt_orderid in vt_orderids:
            self.active_orderids.add(vt_orderid)

        return vt_orderids

    def cancel_order(self, vt_orderid: str) -> None:
        """取消订单"""
        self.strategy_engine.cancel_order(self, vt_orderid)

    def cancel_all(self) -> None:
        """取消所有活跃订单"""
        for vt_orderid in list(self.active_orderids):
            self.cancel_order(vt_orderid)

    def get_pos(self, vt_symbol: str) -> float:
        """查询当前持仓"""
        return self.pos_data[vt_symbol]

    def get_target(self, vt_symbol: str) -> float:
        """查询目标持仓"""
        return self.target_data[vt_symbol]

    def set_target(self, vt_symbol: str, target: float) -> None:
        """设置目标持仓"""
        self.target_data[vt_symbol] = target

    def execute_trading(self, bars: dict[str, BarData], price_add: float) -> None:
        """根据目标执行交易调整"""
        self.cancel_all()

        # 只为有当前K线数据的合约发送订单
        for vt_symbol, bar in bars.items():
            # 计算持仓差异
            target: float = self.get_target(vt_symbol)
            pos: float = self.get_pos(vt_symbol)
            diff: float = target - pos

            # 多头仓位
            if diff > 0:
                # 计算多单价格
                order_price: float = bar.close_price * (1 + price_add)

                # 计算平空和买多的数量
                cover_volume: float = 0
                buy_volume: float = 0

                if pos < 0:
                    cover_volume = min(diff, abs(pos))
                    buy_volume = diff - cover_volume
                else:
                    buy_volume = diff

                # 发送对应订单
                if cover_volume:
                    self.cover(vt_symbol, order_price, cover_volume)

                if buy_volume:
                    self.buy(vt_symbol, order_price, buy_volume)
            # 空头仓位
            elif diff < 0:
                # 计算空单价格
                order_price = bar.close_price * (1 - price_add)

                # 计算卖空和卖出的数量
                sell_volume: float = 0
                short_volume: float = 0

                if pos > 0:
                    sell_volume = min(abs(diff), pos)
                    short_volume = abs(diff) - sell_volume
                else:
                    short_volume = abs(diff)

                # 发送对应订单
                if sell_volume:
                    self.sell(vt_symbol, order_price, sell_volume)

                if short_volume:
                    self.short(vt_symbol, order_price, short_volume)

    def write_log(self, msg: str) -> None:
        """写入日志消息"""
        self.strategy_engine.write_log(msg, self)

    def get_cash_available(self) -> float:
        """获取可用资金"""
        return self.strategy_engine.get_cash_available()

    def get_holding_value(self) -> float:
        """获取持仓市值"""
        return self.strategy_engine.get_holding_value()

    def get_portfolio_value(self) -> float:
        """获取总资产价值"""
        return self.get_cash_available() + self.get_holding_value()

    def get_cash(self) -> float:
        """兼容旧方法"""
        return self.get_cash_available()
