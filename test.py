from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime

# 配置数据服务
datafeed = get_datafeed()

# 创建历史数据请求
req = HistoryRequest(
    symbol="000001",           # 股票代码
    exchange=Exchange.SZSE,    # 深交所
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31),
    interval=Interval.DAILY    # 日K线
)

# 获取数据
datafeed.init()
bars = datafeed.query_bar_history(req, print)

