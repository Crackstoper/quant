# Akshare数据服务快速开始指南

## 🎯 概览

本指南帮助您快速开始使用Akshare数据服务插件，获取股票、期货等金融历史数据。

## 📋 前提条件

### 1. 安装依赖
```bash
pip install akshare pandas polars loguru
```

### 2. 配置环境
确保您已经安装了VeighNa框架及其依赖项。

## ⚙️ 配置步骤

### 方法一：使用配置文件 (推荐)

1. **复制配置文件**:
   ```bash
   cp config/vt_setting_akshare.json config/vt_setting.json
   ```

2. **验证配置**:
   ```json
   {
       "datafeed.name": "akshare",
       "datafeed.username": "",
       "datafeed.password": ""
   }
   ```

### 方法二：通过代码设置

```python
from vnpy.trader.setting import SETTINGS

SETTINGS["datafeed.name"] = "akshare"
```

## 🚀 快速开始

### Python脚本中使用

```python
from datetime import datetime
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest

# 1. 获取数据服务实例
datafeed = get_datafeed()

# 2. 创建请求 - 股票数据
req = HistoryRequest(
    symbol="000001.SZSE",           # 平安银行 (深圳)
    exchange=Exchange.SZSE,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 1),
    interval=Interval.DAILY         # daily, weekly, monthly
)

# 3. 查询数据
bars = datafeed.query_bar_history(req)
print(f"获取到 {len(bars)} 条K线数据")

# 4. 使用数据
if bars:
    bar = bars[0]
    print(f"日期: {bar.datetime.date()}")
    print(f"开盘价: {bar.open_price}")
    print(f"收盘价: {bar.close_price}")
    print(f"最高价: {bar.high_price}")
    print(f"最低价: {bar.low_price}")
    print(f"成交量: {bar.volume}")
```

### Alpha研究工作流集成

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest

# 1. 初始化实验室
lab = AlphaLab("research_data")

# 2. 获取数据服务
datafeed = get_datafeed()

# 3. 下载并保存数据
req = HistoryRequest(
    symbol="000001.SZSE",
    exchange=Exchange.SZSE,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 1, 1),
    interval=Interval.DAILY
)

bars = datafeed.query_bar_history(req)
if bars:
    lab.save_bar_data(bars, "000001")  # 保存到本地数据库
    print("数据已保存到AlphaLab")
```

## 📊 支持的证券类型

### 上海证券交易所 (SSE)
- **A股**: 600000-689999
- **科创板**: 688000-688999

### 深圳证券交易所 (SZSE)
- **A股**: 000000-002999 (主板), 300000-399999 (创业板)
- **B股**: 200000-299999

### 北京证券交易所 (BSE)
- **精选层**: 430000-439999
- **创新层**: 870000-879999

### 示例符号
- `000001.SZSE` - 平安银行
- `600000.SSE` - 浦发银行
- `300001.SZSE` - 特锐德 (创业板)
- `688001.SSE` - 华兴源创 (科创板)

## 🔧 高级用法

### 1. 不同时间周期

```python
# 日线数据
req_daily = HistoryRequest(
    symbol="000001.SZSE",
    exchange=Exchange.SZSE,
    start=datetime(2024, 1, 1),
    interval=Interval.DAILY
)

# 周线数据
req_weekly = HistoryRequest(
    symbol="000001.SZSE",
    exchange=Exchange.SZSE,
    start=datetime(2024, 1, 1),
    interval=Interval.WEEKLY
)

# 月线数据
req_monthly = HistoryRequest(
    symbol="000001.SZSE",
    exchange=Exchange.SZSE,
    start=datetime(2024, 1, 1),
    interval=Interval.MONTHLY
)
```

### 2. 复权选项

```python
# 前复权 (默认)
df_qfq = ak.stock_zh_a_hist(symbol='000001', adjust='qfq')

# 后复权
df_hfq = ak.stock_zh_a_hist(symbol='000001', adjust='hfq')

# 不复权
df_no_adjust = ak.stock_zh_a_hist(symbol='000001', adjust='')
```

### 3. 批量处理多个股票

```python
symbols = ["000001.SZSE", "600000.SSE", "000002.SZSE"]

for symbol in symbols:
    req = HistoryRequest(
        symbol=symbol,
        exchange=Exchange[symbol.split('.')[1]],
        start=datetime(2024, 1, 1),
        end=datetime(2024, 3, 1),
        interval=Interval.DAILY
    )
    bars = datafeed.query_bar_history(req)
    if bars:
        print(f"{symbol}: 获取到 {len(bars)} 条数据")
```

## ⚠️ 注意事项

### 1. 网络连接
- 确保可以访问东方财富网
- 建议在网络环境良好的情况下使用
- 如遇网络问题，请检查代理设置

### 2. 数据限制
- **更新延迟**: 数据通常有15-30分钟的延迟
- **免费用户**: 部分高级功能可能有频率限制
- **API稳定性**: 外部API可能偶发不稳定，建议添加重试机制

### 3. 错误处理

```python
try:
    bars = datafeed.query_bar_history(req)
    if not bars:
        print("未获取到数据，请检查股票代码和日期范围")
except Exception as e:
    print(f"数据获取失败: {e}")
```

## 🧪 测试验证

运行集成测试:
```bash
cd /Users/heshi/Quant/quant
python3 examples/akshare_integration_demo.py
```

或者运行核心功能测试:
```bash
python3 simple_test.py
```

## 📚 更多资源

- [完整文档](AKSHARE_INTEGRATION_SUMMARY.md)
- [API参考](vnpy/alpha/datafeed/README.md)
- [测试用例](tests/test_akshare_datafeed.py)

## ❓ 常见问题

**Q: 初始化时出现网络错误怎么办？**
A: 检查网络连接，确保可以访问东方财富网。如果持续出现问题，请联系网络管理员。

**Q: 获取不到某只股票的数据怎么办？**
A: 确认股票代码正确，检查日期范围是否合理。部分ST股票或退市股票可能没有数据。

**Q: 如何提高数据获取速度？**
A: 建议使用较长的日期范围减少请求次数，避免频繁的小时间段查询。

**Q: Tick数据什么时候支持？**
A: 当前版本暂不支持Tick数据。如需此功能，请关注后续版本更新。

---

**版本**: v1.0.0
**最后更新**: 2026年3月13日