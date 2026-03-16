from vnpy.alpha.datafeed.akshare import AkshareDatafeed
from datetime import datetime
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest, BarData

# 创建实例
datafeed = AkshareDatafeed()
print("✅ 实例创建成功")

# 测试符号转换方法
symbol, exchange = datafeed._convert_vt_to_akshare_symbol("000001")

stock_req = HistoryRequest(
        symbol="000001.SZSE",
        exchange=Exchange.SZSE,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 5, 31),
        interval=Interval.MONTHLY
    )

# 测试时间周期映射
datafeed.init()
bar = datafeed.query_bar_history(stock_req, print)
print(bar)
a=1

