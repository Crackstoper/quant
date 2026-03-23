from vnpy.alpha import AlphaStrategy
from vnpy.trader.object import BarData, TradeData
from vnpy.trader.constant import Direction
import polars as pl

class MA_Strategy(AlphaStrategy):
    """
    MA 均线策略
    - 买入: 价格站上MAn日日线且成交额大于n日均价成交额
    - 卖出: 价格跌破MA5日线（5日均线）

    策略特点:
    - 双均线系统：MA120作为趋势过滤器，MA5作为入场/出场信号
    - 趋势跟踪：只在上涨趋势中持有仓位
    - 风险控制：严格止损，避免大幅回撤
    - 成交额过滤：避免在低流动性时买入，提高交易质量
    - 参数可调：可调整买入/卖出的具体阈值
    """

    def __init__(self, *args, **kwargs):


        # 历史价格数据缓存
        self.price_history = {}  # {vt_symbol: [价格列表]}
        self.volume_history = {}  # {vt_symbol: [成交量列表]}
        self.turnover_history = {}  # {vt_symbol: [成交额列表]}
        self.buy_values = {}   # {vt_symbol: MA120值}
        self.sell_values = {}     # {vt_symbol: MA5值}
        self.turnover_values = {}  # {vt_symbol: 120日成交额均线值}
        self.buy_prices = {}     # {vt_symbol: buy_price}
        self.is_positioned = {}  # {vt_symbol: bool} 是否持有仓位

        # 最小持仓天数，避免频繁交易
        self.min_hold_days = 5
        self.buy_ma = 120
        self.sell_ma = 5
        self.turnover_threshold_ratio = 1.0  # 成交额阈值比例（相对于120日均值）
        super().__init__(*args, **kwargs)


    def on_init(self):
        """策略初始化"""
        self.write_log("MA策略已启动")

        # 初始化数据结构
        for vt_symbol in self.vt_symbols:
            self.price_history[vt_symbol] = []
            self.volume_history[vt_symbol] = []
            self.turnover_history[vt_symbol] = []
            self.buy_values[vt_symbol] = 0.0
            self.sell_values[vt_symbol] = 0.0
            self.turnover_values[vt_symbol] = 0.0
            self.buy_prices[vt_symbol] = 0.0
            self.is_positioned[vt_symbol] = False

    def calculate_moving_average(self, prices, window):
        """计算移动平均线"""
        if len(prices) < window:
            return sum(prices) / len(prices) if prices else 0.0
        return sum(prices[-window:]) / window

    def update_indicators(self, vt_symbol, current_price, current_volume, current_turnover):
        """更新技术指标"""
        if vt_symbol not in self.price_history:
            self.price_history[vt_symbol] = []
            self.volume_history[vt_symbol] = []
            self.turnover_history[vt_symbol] = []

        # 添加新数据
        self.price_history[vt_symbol].append(current_price)
        self.volume_history[vt_symbol].append(current_volume)
        self.turnover_history[vt_symbol].append(current_turnover)

        # 保持足够的历史数据长度
        if len(self.price_history[vt_symbol]) > 150:  # 保留150个历史数据点
            self.price_history[vt_symbol] = self.price_history[vt_symbol][-150:]
            self.volume_history[vt_symbol] = self.volume_history[vt_symbol][-150:]
            self.turnover_history[vt_symbol] = self.turnover_history[vt_symbol][-150:]

        # 计算MA120和MA5
        self.buy_values[vt_symbol] = self.calculate_moving_average(
            self.price_history[vt_symbol], self.buy_ma
        )

        self.sell_values[vt_symbol] = self.calculate_moving_average(
            self.price_history[vt_symbol], self.sell_ma
        )

        # 计算120日成交额均线（只有当有足够数据时才计算）
        if len(self.turnover_history[vt_symbol]) >= self.buy_ma:
            self.turnover_values[vt_symbol] = self.calculate_moving_average(
                self.turnover_history[vt_symbol], self.buy_ma
            )
        else:
            self.turnover_values[vt_symbol] = sum(self.turnover_history[vt_symbol]) / len(self.turnover_history[vt_symbol]) if self.turnover_history[vt_symbol] else 0.0


    def should_buy(self, vt_symbol, current_price, current_turnover):
        """判断是否应该买入"""
        # 检查是否有足够的MA120数据
        if len(self.price_history[vt_symbol]) < 120:
            return False

        # 检查是否已经持有仓位
        if self.is_positioned.get(vt_symbol, False):
            return False

        # 买入条件: 当前价格站上MA120且成交额大于阈值
        min_turnover = self.turnover_values[vt_symbol] * self.turnover_threshold_ratio
        return (current_price > self.buy_values[vt_symbol] and
                current_turnover > min_turnover)

    def should_sell(self, vt_symbol, current_price):
        """判断是否应该卖出"""
        # 检查是否持有仓位
        if not self.is_positioned.get(vt_symbol, False):
            return False

        # 卖出条件: 价格跌破MA5
        return current_price < self.sell_values[vt_symbol]

    def on_trade(self, trade: TradeData):
        """成交回调 - 更新持仓状态"""
        vt_symbol = trade.vt_symbol

        if trade.direction == Direction.LONG:
            # 买入成交
            self.buy_prices[vt_symbol] = trade.price
            self.is_positioned[vt_symbol] = True
            self.write_log(f"买入 {vt_symbol} @ {trade.price:.2f}")
        elif trade.direction == Direction.SHORT:
            # 卖出成交
            self.is_positioned[vt_symbol] = False
            self.write_log(f"卖出 {vt_symbol} @ {trade.price:.2f}")

    def on_bars(self, bars: dict[str, BarData]):
        """K线切片回调 - 主交易逻辑"""
        if not bars:
            return

        for vt_symbol, bar in bars.items():
            current_price = bar.close_price
            bar_datetime = bar.datetime

            # 更新技术指标
            current_volume = bar.volume
            current_turnover = bar.turnover
            self.update_indicators(vt_symbol, current_price, current_volume, current_turnover)

            # 如果还没有买入信号，检查买入条件
            if not self.is_positioned.get(vt_symbol, False):
                if self.should_buy(vt_symbol, current_price, current_turnover):
                    # 执行买入
                    target_volume = 100  # 可配置的手数
                    self.set_target(vt_symbol, target_volume)
                    self.execute_trading(bars, price_add=0.01)
                    self.write_log(f"买入 {vt_symbol} @ {current_price:.2f} (成交量: {current_volume}, 成交额: {current_turnover:.2f})")

            # 如果已经持有仓位，检查卖出条件
            else:
                if self.should_sell(vt_symbol, current_price):
                    # 执行卖出
                    self.set_target(vt_symbol, 0)
                    self.execute_trading(bars, price_add=0.01)
                    self.write_log(f"{bar_datetime.strftime('%Y-%m-%d')} 卖出 {vt_symbol} @ {current_price:.2f}")