# CLAUDE_zh.md

此文件为 Claude Code (claude.ai/code) 在处理此仓库代码时提供指导。

## 命令

### 开发环境设置
- `python -m venv .venv && source .venv/bin/activate` - 创建并激活虚拟环境
- `pip install -e .[alpha,dev]` - 以开发模式安装包，包含 alpha 和 dev 依赖
- `python run.py` - 启动 VeighNa 交易终端 GUI 应用程序
- `python -m pytest tests/ -v` - 运行所有测试
- `python -m pytest tests/test_alpha101.py -v` - 专门运行 alpha101 测试
- `ruff check .` - 使用 ruff 检查代码风格
- `mypy vnpy` - 运行静态类型检查
- `python -c "from vnpy import __version__; print(__version__)"` - 检查已安装版本

### 构建和分发
- `python -m build` - 构建包分发
- `python -m twine upload dist/*` - 上传到 PyPI（需要凭据）

### Alpha 模块（AI 驱动量化研究）
- `python examples/alpha_research/download_data_rq.ipynb` - 运行 RQData 下载演示
- `python examples/alpha_research/research_workflow_lasso.ipynb` - 运行 Lasso 回归工作流
- `python examples/alpha_research/research_workflow_lgb.ipynb` - 运行 LightGBM 工作流
- `python examples/alpha_research/research_workflow_mlp.ipynb` - 运行 MLP 神经网络工作流

## 架构总览

VeighNa 是一个全面的量化交易框架，包含三个主要架构层次：

### 1. 核心框架 (vnpy 包)
- **event/**: 核心事件驱动架构，EventEngine 实现发布/订阅模式
- **trader/**: 主交易平台，包含引擎、网关和数据对象
- **chart/**: 高性能图表，支持实时数据可视化
- **rpc/**: 跨进程通信，用于分布式系统

### 2. 交易平台 (vnpy.trader)
框架的核心，提供：
- **MainEngine**: 中央引擎，协调所有交易功能
- **BaseEngine/BaseApp**: 策略引擎和应用程序的抽象类
- **BaseGateway**: 连接到交易场所的抽象接口
- **事件系统**: 为 ticks、订单、交易、持仓等自定义事件类型
- **数据对象**: TickData、BarData、OrderData、TradeData 等，使用 VT（VeighNa 交易）符号格式

关键文件：
- `vnpy/trader/engine.py`: MainEngine 实现
- `vnpy/trader/gateway.py`: BaseGateway 实现
- `vnpy/trader/event.py`: 事件常量
- `vnpy/trader/object.py`: 数据对象定义

### 3. AI 驱动 Alpha 模块 (vnpy.alpha)
v4.0 新增，提供完整的基于机器学习的量化研究工作流：
- **lab.py**: Alpha 研究实验室，管理数据、模型和策略
- **dataset/**: 因子特征工程，包含 Alpha 158 表达式
- **model/**: ML 模型实现（Lasso、LightGBM、MLP）
- **strategy/**: 基于 ML 的交易策略模板

关键能力：
- 因子计算引擎，包含时间序列和截面函数
- 标准化的 ML 模型开发流水线
- 集成回测和研究工作流
- 支持多个因子库（来自微软 Qlib 的 Alpha 158）

### 4. 网关系统
连接到各种交易场所：
- CTP、CTP Mini、CTP 证券
- Interactive Brokers、TAP（易盛外盘）
- RQData、XT（迅投研）数据源
- REST、WebSocket 客户端
- 期权、价差交易的专业网关

### 5. 应用程序模块
特定用例的预构建应用程序：
- CTA 策略引擎
- 回测器
- 组合策略
- 价差交易
- 期权大师
- 算法交易
- 纸面交易
- 数据管理器/记录器
- 风险管理器
- Web 交易器

## 关键设计模式

### 事件驱动架构
- EventEngine 发布/订阅模式
- 每个数据类别的自定义事件类型
- 定时事件用于周期性处理
- 处理器注册/注销系统

### VT 符号系统
- `<网关>.<代码>` 格式（例如 "CTP.SHFE.rb2401"）
- 跨网关的一致符号表示
- VT 前缀用于内部事件处理

### 网关模式
- 抽象 BaseGateway 用于场所连接
- 网关实现处理场所特定协议
- 统一接口用于交易操作
- 自动符号转换和数据标准化

## Alpha 模块工作流

1. **数据准备**: 使用 AlphaDataset 加载市场数据
2. **因子计算**: 应用时间序列和截面函数
3. **模型训练**: 使用标准化的 AlphaModel 接口训练 ML 模型
4. **策略开发**: 创建使用 ML 信号的策略
5. **回测**: 使用集成实验室工作流进行测试
6. **研究**: 利用内置分析和可视化工具

## 开发指南

### 代码风格
- 遵循 PEP 8，使用 ruff 检查
- 所有函数定义都需要类型提示
- 适当使用越南语/英语双语注释
- 事件处理器应该轻量快速

### 测试
- Alpha 101 测试用于因子计算
- 网关测试用于连接验证
- 策略测试用于交易逻辑
- 使用 pytest 执行测试

### 国际化
- 使用 `_()` 函数进行字符串本地化
- 区域设置文件在 `vnpy/trader/locale/`
- 支持英语和中文

## 常见任务

### 添加新网关
1. 创建网关模块，包含 BaseGateway 实现
2. 实现场所特定的连接逻辑
3. 处理场所特定的数据格式
4. 将网关注册到 MainEngine

### 创建新策略应用
1. 创建应用模块，包含 BaseApp 实现
2. 实现继承自 BaseEngine 的策略引擎
3. 创建策略配置的 UI 组件
4. 将应用注册到 MainEngine

### Alpha 研究工作流
1. 使用数据路径初始化 AlphaLab
2. 使用 AlphaDataset 加载数据
3. 使用内置函数计算因子
4. 使用 AlphaModel 接口训练模型
5. 生成信号并回测策略
6. 使用实验室可视化工具分析结果