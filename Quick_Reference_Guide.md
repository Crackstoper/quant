# VeighNa 快速参考指南

> **零基础小白的速查手册**

## 📚 目录

1. [快速开始](#快速开始)
2. [常用命令](#常用命令)
3. [核心概念](#核心概念)
4. [文件位置](#文件位置)
5. [API速查](#api速查)
6. [常见问题](#常见问题)

---

## 快速开始

### 🚀 5分钟启动

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 2. 安装VeighNa
pip install -e .[alpha,dev]

# 3. 运行示例
python examples/veighna_trader/run.py
```

### 📝 最小启动脚本

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_ctp import CtpGateway

def main():
    # 创建应用
    qapp = create_qapp()

    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)

    # 添加网关
    main_engine.add_gateway(CtpGateway)

    # 创建窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    # 启动
    qapp.exec()

if __name__ == "__main__":
    main()
```

---

## 常用命令

### 🛠️ 开发环境

| 命令 | 说明 |
|------|------|
| `python -m venv .venv` | 创建虚拟环境 |
| `source .venv/bin/activate` | 激活环境(Linux/Mac) |
| `.venv\Scripts\activate` | 激活环境(Windows) |
| `pip install -e .[alpha,dev]` | 安装开发版本 |

### 🧪 测试和检查

| 命令 | 说明 |
|------|------|
| `python -m pytest tests/ -v` | 运行所有测试 |
| `python -m pytest tests/test_alpha101.py -v` | 运行Alpha101测试 |
| `ruff check .` | 代码风格检查 |
| `mypy vnpy` | 类型检查 |

### 📊 Alpha研究

| 命令 | 说明 |
|------|------|
| `jupyter notebook` | 启动Jupyter |
| `python examples/alpha_research/download_data_rq.ipynb` | 下载RQData数据 |
| `python examples/alpha_research/research_workflow_lgb.ipynb` | LGB研究工作流 |

### 🏗️ 构建和发布

| 命令 | 说明 |
|------|------|
| `python -m build` | 构建包 |
| `python -m twine upload dist/*` | 上传到PyPI |

---

## 核心概念

### 🏗️ 三大核心组件

| 组件 | 职责 | 关键类 |
|------|------|--------|
| **EventEngine** | 事件处理 | `EventEngine` |
| **MainEngine** | 核心引擎 | `MainEngine` |
| **BaseGateway** | 交易所连接 | `BaseGateway` |

### 📊 核心数据对象

| 对象 | 说明 | 主要用途 |
|------|------|----------|
| `TickData` | Tick行情数据 | 实时价格信息 |
| `BarData` | K线数据 | 技术分析 |
| `OrderData` | 订单数据 | 订单状态跟踪 |
| `TradeData` | 成交数据 | 交易记录 |
| `PositionData` | 持仓数据 | 仓位管理 |
| `AccountData` | 账户数据 | 资金管理 |

### 🔄 事件类型

| 事件 | 触发时机 | 数据对象 |
|------|----------|----------|
| `EVENT_TICK` | 收到行情 | `TickData` |
| `EVENT_BAR` | K线更新 | `BarData` |
| `EVENT_ORDER` | 订单状态变化 | `OrderData` |
| `EVENT_TRADE` | 成交回报 | `TradeData` |
| `EVENT_POSITION` | 持仓变化 | `PositionData` |

### 🎯 VT符号格式

```
<网关>.<代码>

示例：
- CTP.SHFE.rb2401    # 期货合约
- IB.SMART.AAPL      # 股票
- RQData.000001.SZ   # 股票
```

---

## 文件位置

### 📁 重要文件路径

| 功能 | 文件路径 | 说明 |
|------|----------|------|
| 主引擎 | `vnpy/trader/engine.py` | 核心引擎实现 |
| 网关基类 | `vnpy/trader/gateway.py` | 网关接口定义 |
| 数据对象 | `vnpy/trader/object.py` | 所有数据类 |
| 事件引擎 | `vnpy/event/event_engine.py` | 事件处理系统 |
| Alpha实验室 | `vnpy/alpha/lab.py` | AI研究平台 |
| Alpha158因子 | `vnpy/alpha/dataset/datasets/alpha_158.py` | 因子库 |

### 📚 示例代码位置

| 功能 | 路径 | 说明 |
|------|------|------|
| 交易界面 | `examples/veighna_trader/` | 标准启动示例 |
| Alpha研究 | `examples/alpha_research/` | Jupyter笔记本 |
| RPC通信 | `examples/client_server/` | 客户端服务器 |
| 数据记录 | `examples/data_recorder/` | 行情记录 |

### 🧪 测试文件位置

| 功能 | 路径 | 说明 |
|------|------|------|
| Alpha101测试 | `tests/test_alpha101.py` | 因子计算测试 |
| 事件引擎测试 | `tests/test_event_engine.py` | 事件处理测试 |
| 网关测试 | `tests/test_gateway.py` | 网关接口测试 |

---

## API速查

### 🏗️ MainEngine API

```python
# 创建引擎
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine

event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 添加网关
from vnpy_ctp import CtpGateway
main_engine.add_gateway(CtpGateway)

# 添加应用
from vnpy_ctastrategy import CtaStrategyApp
main_engine.add_app(CtaStrategyApp)

# 连接网关
main_engine.connect("CTP")

# 发送订单
from vnpy.trader.object import OrderRequest
req = OrderRequest(
    symbol="rb2401",
    exchange=Exchange.SHFE,
    direction=Direction.LONG,
    offset=Offset.OPEN,
    price=3800.0,
    volume=1
)
main_engine.send_order(req, "CTP")
```

### 📊 AlphaLab API

```python
from vnpy.alpha.lab import AlphaLab

# 创建实验室
lab = AlphaLab("my_research")

# 加载数据
dataset = lab.load_data(
    symbols=["000001.SZ", "000002.SZ"],
    start_date="20200101",
    end_date="20231231"
)

# 添加因子
dataset.add_factor("alpha_158")

# 训练模型
model = lab.train_model("lgb", dataset)

# 生成信号
signals = lab.generate_signal(model, dataset)

# 回测
results = lab.backtest(signals)
```

### 🎯 CTA策略模板

```python
from vnpy_ctastrategy import CtaTemplate, CtaEngine
from vnpy.trader.object import TickData, BarData

class MyStrategy(CtaTemplate):
    """我的策略"""

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """Tick行情回调"""
        # 策略逻辑
        pass

    def on_bar(self, bar: BarData):
        """K线回调"""
        # 策略逻辑
        pass
```

### 🌐 网关接口

```python
from vnpy.trader.gateway import BaseGateway

class MyGateway(BaseGateway):
    """我的网关"""

    def connect(self):
        """连接交易所"""
        pass

    def subscribe(self, req):
        """订阅行情"""
        pass

    def send_order(self, req):
        """发送订单"""
        pass

    def cancel_order(self, req):
        """撤单"""
        pass
```

---

## 常见问题

### 🚫 启动问题

**Q: 运行 `python run.py` 报错 "ModuleNotFoundError"**

A: 未正确安装依赖，运行：
```bash
pip install -e .[alpha,dev]
```

**Q: Qt界面无法显示**

A: 缺少PyQt5，运行：
```bash
pip install PyQt5
```

### 📊 数据问题

**Q: 如何获取历史数据？**

A: 使用Alpha模块：
```python
from vnpy.alpha.lab import AlphaLab
lab = AlphaLab("data")
dataset = lab.load_data(symbols=["000001.SZ"])
```

**Q: 如何订阅实时行情？**

A: 使用订阅请求：
```python
from vnpy.trader.object import SubscribeRequest
req = SubscribeRequest(symbol="rb2401", exchange=Exchange.SHFE)
main_engine.subscribe(req, "CTP")
```

### 🤖 AI模块问题

**Q: 如何添加自定义因子？**

A: 使用AlphaDataset：
```python
dataset.add_factor("my_factor", my_factor_func)
```

**Q: 如何训练自定义模型？**

A: 继承AlphaModel：
```python
from vnpy.alpha.model import AlphaModel

class MyModel(AlphaModel):
    def fit(self, X, y):
        # 训练逻辑
        pass
```

### 🧪 测试问题

**Q: 如何运行特定测试？**

A: 使用pytest：
```bash
python -m pytest tests/test_alpha101.py -v
```

**Q: 代码风格检查失败？**

A: 修复ruff问题：
```bash
ruff check .
ruff format .
```

---

## 🎯 快速调试

### 📝 日志查看

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 在策略中写日志
self.write_log("这是调试信息")
```

### 🔍 事件调试

```python
# 注册事件处理器查看事件流
def debug_handler(event):
    print(f"收到事件: {event.type}, 数据: {event.data}")

event_engine.register(EVENT_TICK, debug_handler)
```

### 📊 数据检查

```python
# 查看Tick数据结构
print(tick.__dict__)

# 查看Bar数据
print(f"开盘: {bar.open_price}, 收盘: {bar.close_price}")
```

---

## 🎓 学习资源

### 📚 官方文档
- [VeighNa文档](https://www.vnpy.com/docs/cn/index.html)
- [社区论坛](https://www.vnpy.com/forum/)

### 📖 代码学习
1. 从 `examples/veighna_trader/run.py` 开始
2. 学习 `vnpy/trader/object.py` 数据对象
3. 研究 `examples/alpha_research/` 示例

### 💬 社区支持
- QQ群: 262656087
- 微信群: 扫描README二维码

---

## 🚀 进阶路径

### 阶段1: 基础使用
- ✅ 运行示例代码
- ✅ 理解核心概念
- ✅ 修改策略参数

### 阶段2: 策略开发
- ✅ 编写简单策略
- ✅ 使用回测系统
- ✅ 参数优化

### 阶段3: AI研究
- ✅ 运行Alpha示例
- ✅ 自定义因子
- ✅ 模型训练

### 阶段4: 系统开发
- ✅ 开发新网关
- ✅ 创建应用模块
- ✅ 贡献代码

---

## 🎉 总结

这个快速参考指南提供了：

- 🚀 **快速开始**: 5分钟启动指南
- 📝 **常用命令**: 开发、测试、研究命令
- 🎯 **核心概念**: 关键组件和数据对象
- 📁 **文件位置**: 重要文件路径
- 💻 **API速查**: 常用接口示例
- ❓ **常见问题**: 典型问题解决方案

保存这份指南，随时查阅！📚✨