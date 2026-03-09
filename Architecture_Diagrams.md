# VeighNa 架构图示详解

> **可视化项目结构与调用逻辑**

## 📊 目录

1. [整体架构图](#整体架构图)
2. [核心组件交互图](#核心组件交互图)
3. [事件处理流程图](#事件处理流程图)
4. [数据流动图](#数据流动图)
5. [AI Alpha模块架构](#ai-alpha模块架构)
6. [网关系统架构](#网关系统架构)
7. [应用模块架构](#应用模块架构)

---

## 整体架构图

### 🏗️ 系统分层架构

```mermaid
flowchart TD
    subgraph "用户层"
        A1[VeighNa Trader UI]
        A2[Web Trader]
        A3[Excel RTD]
        A4[命令行接口]
    end

    subgraph "应用层"
        B1[CTA策略]
        B2[回测引擎]
        B3[组合策略]
        B4[算法交易]
        B5[期权大师]
        B6[风险管理]
    end

    subgraph "核心层"
        C1[MainEngine]
        C2[EventEngine]
        C3[BaseGateway]
        C4[BaseApp]
        C5[数据对象]
    end

    subgraph "接口层"
        D1[CTP网关]
        D2[IB网关]
        D3[RQData]
        D4[数据库]
        D5[文件系统]
    end

    subgraph "外部系统"
        E1[交易所]
        E2[数据供应商]
        E3[数据库服务器]
    end

    A1 --> B1
    A2 --> B2
    B1 --> C1
    B2 --> C1
    C1 --> C2
    C1 --> C3
    C3 --> D1
    C3 --> D2
    D1 --> E1
    D2 --> E1
    D3 --> E2
```

### 🔄 运行时架构

```mermaid
graph TB
    subgraph "主进程"
        A[Main Thread] --> B[Event Loop]
        B --> C[UI Thread]
        B --> D[Gateway Thread]
        B --> E[Strategy Thread]
    end

    subgraph "子进程"
        F[RPC Server]
        G[Data Recorder]
        H[Risk Manager]
    end

    C --> I[Qt GUI]
    D --> J[网络IO]
    E --> K[策略逻辑]

    F --> L[跨进程通信]
    G --> M[数据持久化]
    H --> N[风险控制]
```

---

## 核心组件交互图

### 🏗️ MainEngine 组件关系

```mermaid
classDiagram
    class MainEngine {
        -event_engine: EventEngine
        -gateways: Dict[str, BaseGateway]
        -apps: Dict[str, BaseApp]
        -engines: Dict[str, BaseEngine]
        +add_gateway(gateway: Type[BaseGateway])
        +add_app(app: Type[BaseApp])
        +connect(gateway_name: str)
        +subscribe(req: SubscribeRequest, gateway_name: str)
        +send_order(req: OrderRequest, gateway_name: str)
        +cancel_order(req: CancelRequest, gateway_name: str)
    }

    class EventEngine {
        -event_queue: Queue
        -handlers: Dict[str, List[Callable]]
        -active: bool
        +register(event_type: str, handler: Callable)
        +unregister(event_type: str, handler: Callable)
        +put(event: Event)
        +process()
        +start()
        +stop()
    }

    class BaseGateway {
        #main_engine: MainEngine
        #event_engine: EventEngine
        #gateway_name: str
        +connect()
        +subscribe(req: SubscribeRequest)
        +send_order(req: OrderRequest)
        +cancel_order(req: CancelRequest)
        +close()
    }

    class BaseApp {
        +app_name: str
        +app_display_name: str
        +app_engine: BaseEngine
        +create_engine(main_engine: MainEngine, event_engine: EventEngine)
    }

    MainEngine --> EventEngine
    MainEngine --> BaseGateway
    MainEngine --> BaseApp
    BaseApp --> BaseEngine
```

### 🔄 事件处理机制

```mermaid
sequenceDiagram
    participant Gateway
    participant EventEngine
    participant Handler1
    participant Handler2
    participant Handler3

    Gateway->>EventEngine: 创建事件
    EventEngine->>EventEngine: 放入事件队列
    loop 事件处理循环
        EventEngine->>EventEngine: 获取事件
        EventEngine->>Handler1: 调用处理器1
        EventEngine->>Handler2: 调用处理器2
        EventEngine->>Handler3: 调用处理器3
    end
```

---

## 事件处理流程图

### 📡 行情数据处理流程

```mermaid
flowchart TD
    A[交易所] -->|原始行情| B(Gateway)
    B -->|解析数据| C{数据验证}
    C -->|有效| D[创建TickData]
    C -->|无效| E[丢弃数据]
    D --> F[发布EVENT_TICK]
    F --> G[EventEngine]
    G --> H{事件分发}
    H -->|策略订阅| I[CTA策略]
    H -->|数据记录| J[Data Recorder]
    H -->|图表更新| K[Chart Widget]
    H -->|风险管理| L[Risk Manager]
```

### 📤 订单处理流程

```mermaid
flowchart LR
    A[策略逻辑] -->|生成信号| B[创建OrderRequest]
    B --> C[MainEngine.send_order]
    C --> D[Gateway.send_order]
    D --> E[交易所]
    E -->|订单确认| F[Gateway.on_order]
    F --> G[发布EVENT_ORDER]
    G --> H[EventEngine]
    H --> I[策略更新状态]
    H --> J[UI更新显示]
    H --> K[风险检查]
```

### 💰 成交处理流程

```mermaid
sequenceDiagram
    participant Exchange
    participant Gateway
    participant EventEngine
    participant Strategy
    participant RiskManager
    participant Database

    Exchange->>Gateway: 成交回报
    Gateway->>Gateway: 解析成交数据
    Gateway->>Gateway: 创建TradeData
    Gateway->>EventEngine: 发布EVENT_TRADE
    EventEngine->>Strategy: 更新策略状态
    EventEngine->>RiskManager: 风险检查
    EventEngine->>Database: 保存成交记录
    EventEngine->>Strategy: 触发策略回调
```

---

## 数据流动图

### 🔄 完整数据流

```mermaid
flowchart TD
    subgraph "外部数据源"
        A1[交易所行情]
        A2[数据供应商]
        A3[数据库]
    end

    subgraph "VeighNa系统"
        B1[Gateway]
        B2[EventEngine]
        B3[MainEngine]
        B4[Strategy Engine]
        B5[Risk Engine]
        B6[Data Manager]
    end

    subgraph "应用层"
        C1[CTA策略]
        C2[回测引擎]
        C3[图表显示]
        C4[数据导出]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B6

    B1 --> B2
    B2 --> B3
    B3 --> B4
    B3 --> B5
    B3 --> B6

    B4 --> C1
    B6 --> C2
    B2 --> C3
    B6 --> C4
```

### 📊 数据存储架构

```mermaid
graph TB
    subgraph "内存数据"
        A1[Tick缓存]
        A2[Bar缓存]
        A3[持仓数据]
        A4[账户信息]
    end

    subgraph "持久化存储"
        B1[SQLite]
        B2[MySQL]
        B3[PostgreSQL]
        B4[MongoDB]
        B5[文件系统]
    end

    subgraph "数据访问层"
        C1[Database Manager]
        C2[Data Loader]
        C3[Data Saver]
    end

    A1 --> C3
    A2 --> C3
    A3 --> C3
    A4 --> C3

    C1 --> B1
    C1 --> B2
    C1 --> B3
    C1 --> B4
    C1 --> B5

    B1 --> C2
    B2 --> C2
    B3 --> C2
    B4 --> C2
    B5 --> C2
```

---

## AI Alpha模块架构

### 🧠 Alpha研究实验室架构

```mermaid
classDiagram
    class AlphaLab {
        -lab_path: Path
        -daily_path: Path
        -minute_path: Path
        -component_path: Path
        -dataset_path: Path
        -model_path: Path
        -signal_path: Path
        +load_data(symbols, start_date, end_date)
        +add_factor(name, func)
        +train_model(model_type, dataset)
        +generate_signal(model, dataset)
        +backtest(strategy, signals)
        +analyze(results)
    }

    class AlphaDataset {
        -data: pl.DataFrame
        -symbols: List[str]
        -start_date: datetime
        -end_date: datetime
        +add_time_series_factor(func, window)
        +add_cross_sectional_factor(func)
        +get_features()
        +get_labels()
    }

    class AlphaModel {
        -model: Any
        -model_type: str
        -params: Dict
        +fit(X, y)
        +predict(X)
        +save(path)
        +load(path)
    }

    class AlphaStrategy {
        -lab: AlphaLab
        -model: AlphaModel
        -signals: pl.DataFrame
        +generate_signals(data)
        +execute_trades(signals)
    }

    AlphaLab --> AlphaDataset
    AlphaLab --> AlphaModel
    AlphaLab --> AlphaStrategy
```

### 📊 因子计算流程

```mermaid
flowchart LR
    A[原始数据] --> B{数据预处理}
    B -->|清洗| C[标准化]
    B -->|填充| D[缺失值处理]
    B -->|去极值| E[异常值处理]

    C --> F{因子类型}
    D --> F
    E --> F

    F -->|时间序列| G[滚动窗口计算]
    F -->|截面数据| H[多标的分析]
    F -->|量价关系| I[成交量因子]
    F -->|资金流向| J[资金流因子]

    G --> K[因子矩阵]
    H --> K
    I --> K
    J --> K

    K --> L[特征选择]
    L --> M[模型训练]
```

### 🤖 模型训练流程

```mermaid
flowchart TD
    A[因子矩阵] --> B{数据分割}
    B -->|训练集| C[模型训练]
    B -->|验证集| D[参数调优]
    B -->|测试集| E[性能评估]

    C --> F{模型选择}
    F -->|Lasso| G[L1正则化]
    F -->|LightGBM| H[梯度提升]
    F -->|MLP| I[神经网络]

    G --> J[交叉验证]
    H --> J
    I --> J

    J --> K[模型评估]
    K -->|MSE| L[均方误差]
    K -->|IC| M[信息系数]
    K -->|RankIC| N[秩相关系数]

    L --> O[模型保存]
    M --> O
    N --> O
```

---

## 网关系统架构

### 🌐 网关接口架构

```mermaid
classDiagram
    class BaseGateway {
        #main_engine: MainEngine
        #event_engine: EventEngine
        #gateway_name: str
        #gateway_display_name: str
        #gateway_type: GatewayType
        +connect(req: ConnectRequest)
        +subscribe(req: SubscribeRequest)
        +send_order(req: OrderRequest)
        +cancel_order(req: CancelRequest)
        +send_quote(req: QuoteRequest)
        +cancel_quote(req: CancelQuoteRequest)
        +query_history(req: HistoryRequest)
        +close()
    }

    class CtpGateway {
        -md_api: CThostFtdcMdApi
        -td_api: CThostFtdcTraderApi
        +on_front_connected()
        +on_rsp_user_login()
        +on_rtn_depth_market_data()
        +on_rsp_order_insert()
        +on_rtn_order()
        +on_rtn_trade()
    }

    class IbGateway {
        -ib: EClient
        -wrapper: VnWrapper
        +connection_connected()
        +error()
        +tick_price()
        +tick_size()
        +order_status()
    }

    BaseGateway <|-- CtpGateway
    BaseGateway <|-- IbGateway
```

### 🔄 网关通信流程

```mermaid
sequenceDiagram
    participant MainEngine
    participant Gateway
    participant API
    participant Exchange

    MainEngine->>Gateway: connect()
    Gateway->>API: 初始化API
    API->>Exchange: 建立连接
    Exchange-->>API: 连接确认
    API-->>Gateway: 连接成功
    Gateway-->>MainEngine: 连接完成

    MainEngine->>Gateway: subscribe()
    Gateway->>API: 订阅行情
    API->>Exchange: 发送订阅请求
    loop 行情推送
        Exchange-->>API: 推送Tick数据
        API-->>Gateway: 回调on_tick
        Gateway-->>MainEngine: 发布EVENT_TICK
    end
```

---

## 应用模块架构

### 🏛️ 应用模块关系

```mermaid
graph TB
    A[BaseApp] --> B[CTA策略]
    A --> C[回测引擎]
    A --> D[组合策略]
    A --> E[算法交易]
    A --> F[期权大师]

    B --> G[策略模板]
    B --> H[参数管理]
    B --> I[状态跟踪]

    C --> J[历史回测]
    C --> K[参数优化]
    C --> L[绩效分析]

    D --> M[组合管理]
    D --> N[风险分散]
    D --> O[动态调仓]

    E --> P[算法模板]
    E --> Q[订单拆分]
    E --> R[智能路由]

    F --> S[期权定价]
    F --> T[希腊值计算]
    F --> U[波动率曲面]
```

### 📈 CTA策略引擎

```mermaid
classDiagram
    class CtaEngine {
        -main_engine: MainEngine
        -event_engine: EventEngine
        -strategies: Dict[str, CtaTemplate]
        +add_strategy()
        +init_strategy()
        +start_strategy()
        +stop_strategy()
        +remove_strategy()
    }

    class CtaTemplate {
        #engine: CtaEngine
        #strategy_name: str
        #vt_symbol: str
        #setting: Dict
        +on_init()
        +on_start()
        +on_stop()
        +on_tick(tick: TickData)
        +on_bar(bar: BarData)
        +on_order(order: OrderData)
        +on_trade(trade: TradeData)
    }

    CtaEngine --> CtaTemplate
```

### 🔄 策略执行流程

```mermaid
flowchart TD
    A[策略初始化] --> B{策略状态}
    B -->|已启动| C[接收行情]
    B -->|已停止| D[等待启动]

    C --> E{信号生成}
    E -->|买入信号| F[创建买单]
    E -->|卖出信号| G[创建卖单]
    E -->|无信号| H[继续监听]

    F --> I[发送订单]
    G --> I
    I --> J[等待成交]
    J --> K{成交确认}
    K -->|部分成交| L[更新持仓]
    K -->|完全成交| M[策略回调]
    L --> N[继续监控]
    M --> N
```

---

## 总结

通过这些架构图，我们可以清晰地看到VeighNa框架的：

1. **模块化设计**: 各组件职责明确，易于扩展
2. **事件驱动**: 高效处理实时数据流
3. **分层架构**: 用户界面、业务逻辑、数据访问分离
4. **插件系统**: 支持多种交易接口和应用模块
5. **AI集成**: 完整的机器学习研究到交易的工作流

这些图表为理解和使用VeighNa框架提供了直观的视觉指导。🚀