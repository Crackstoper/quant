# Akshare数据服务插件

## 简介

Akshare是VeighNa框架的第三方数据服务插件，通过[akshare](https://github.com/akshare-tool/akshare)库提供股票、期货等金融数据的获取服务。

## 功能特性

- ✅ **股票历史K线数据**: 支持沪深京A股的历史日线、周线、月线数据
- ✅ **期货历史K线数据**: 支持主要期货品种的历史数据（API可用性取决于akshare版本）
- ✅ **多交易所支持**: 上海证券交易所(SSE)、深圳证券交易所(SZSE)、北京证券交易所(BSE)
- ✅ **复权选项**: 支持前复权(qfq)、后复权(hfq)、不复权(默认)
- ✅ **灵活的时间周期**: daily, weekly, monthly
- ❌ **Tick数据**: 暂不支持历史Tick数据查询

## 安装要求

```bash
pip install akshare
```

## 配置方法

在`vt_setting.json`中配置数据服务：

```json
{
    "datafeed.name": "akshare",
    "datafeed.username": "",
    "datafeed.password": ""
}
```

## 使用示例

### Python脚本中使用

```python
from datetime import datetime
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.datafeed import get_datafeed
from vnpy.trader.object import HistoryRequest

# 获取数据服务实例
datafeed = get_datafeed()

# 创建历史数据请求
req = HistoryRequest(
    symbol="000001",           # 平安银行股票代码
    exchange=Exchange.SZSE,    # 深圳证券交易所
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 1),
    interval=Interval.DAILY
)

# 查询历史K线数据
bars = datafeed.query_bar_history(req)
print(f"获取到 {len(bars)} 条K线数据")

# 打印第一条数据
if bars:
    bar = bars[0]
    print(f"日期: {bar.datetime}, 开盘: {bar.open_price}, "
          f"收盘: {bar.close_price}, 成交量: {bar.volume}")
```

### Alpha研究工作流中使用

```python
from vnpy.alpha.lab import AlphaLab
from vnpy.alpha.dataset.template import AlphaDataset

# 初始化Alpha实验室
lab = AlphaLab("data_path")

# 加载数据服务
datafeed = get_datafeed()

# 下载并保存数据
req = HistoryRequest(
    symbol="000001",
    exchange=Exchange.SZSE,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 1, 1),
    interval=Interval.DAILY
)

bars = datafeed.query_bar_history(req)
if bars:
    lab.save_bar_data(bars, "000001")
```

## 符号映射规则

| VT符号格式 | akshare符号 | 说明 |
|-----------|-------------|------|
| `000001.SZSE` | `000001` | 深圳证券交易所股票 |
| `600000.SSE` | `600000` | 上海证券交易所股票 |
| `000002.SZSE` | `000002` | 深圳证券交易所股票 |
| `600036.SSE` | `600036` | 上海证券交易所股票 |

## 支持的证券范围

### 上海证券交易所 (SSE)
- A股: 600000-689999
- 科创板: 688000-688999

### 深圳证券交易所 (SZSE)
- A股: 000000-002999 (主板), 300000-399999 (创业板)
- B股: 200000-299999

### 北京证券交易所 (BSE)
- A股: 430000-439999, 870000-879999

## API调用限制

1. **网络请求频率**: 建议控制请求频率，避免被反爬虫机制限制
2. **数据更新延迟**: akshare数据通常有15-30分钟的延迟
3. **免费用户限制**: 部分高级功能可能需要付费订阅

## 故障排除

### 常见问题

**Q: 初始化失败**
A: 检查网络连接，确保可以访问东方财富网

**Q: 获取不到数据**
A: 确认股票代码正确，检查日期范围是否合理

**Q: 数据格式错误**
A: 更新akshare到最新版本：`pip install --upgrade akshare`

### 日志调试

启用详细日志输出：

```python
def debug_output(msg):
    print(f"[DEBUG] {msg}")

# 初始化数据服务时传入debug_output函数
datafeed = AkshareDatafeed()
datafeed.init(output=debug_output)
```

## 性能优化建议

1. **批量请求**: 尽量使用较长的日期范围减少请求次数
2. **缓存策略**: 对常用数据进行本地缓存
3. **异步处理**: 对于大量数据下载，建议使用异步方式

## 注意事项

1. akshare是开源项目，其数据源来自东方财富网，请遵守相关使用条款
2. 本插件仅用于学习和研究目的，不建议用于高频交易
3. 数据仅供参考，不构成投资建议
4. 使用前请确保已阅读并理解akshare的使用许可协议