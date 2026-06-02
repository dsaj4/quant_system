# Quant System 当前项目状态与模块讲解

日期：2026-06-02  
状态：Phase 0 到 Phase 8 长期改造已完成并验证
用途：给客户讲清楚“系统现在能做什么、每个模块负责什么、下一步为什么要优化前端体验”。本文不深入展开底层技术架构，只解释模块功能、实现逻辑和可展示边界。

相关最新文档：

- `docs/demo-runbook.md`：本地复跑和演示操作路径
- `docs/demo-checklist.md`：演示前后的检查清单
- `docs/customer-demo-talk-track.md`：客户讲解话术与边界
- `docs/database-roadmap.md`：数据库从 SQLite 走向 PostgreSQL/TimescaleDB 的路线
- `docs/frontend-agent-work-spec.md`：下一位前端优化 agent 的工作规范
- `docs/plans/2026-06-02-long-term-quant-system-upgrade.md`：长期改造总规范
- `docs/stage-records/`：Phase 0 到 Phase 8 的阶段记录

## 一句话

当前项目是一个“内部量化工作台 + 客户只读报告系统”：内部人员可以管理标的、导入真实行情、配置策略、运行回测、生成报告快照、创建分享链接；客户只通过 token 链接查看已经发布的只读报告。

## 类比

可以把它理解成一间小型投研工作室：

```text
研究员/操作员
  -> 准备股票和行情数据
  -> 配置策略参数
  -> 运行历史回测
  -> 审核结果并发布报告
  -> 给客户一条只读链接

客户
  -> 打开链接
  -> 只看已经审定的报告
  -> 不能改参数，不能触发交易
```

这个类比的边界是：系统目前不是实盘交易系统，也不是完整投顾合规平台。它更像可演示、可复核、可发布报告的量化策略样机。

## 当前状态

| 事项 | 状态 | 说明 |
|---|---|---|
| 后端 API | 已实现并测试 | FastAPI 提供登录、行情、策略、回测、报告、模拟运行、日志、健康检查等接口 |
| 真实数据源 | 已接入第一批 | Tushare Pro 已作为主源接入；AkShare 保留免费兜底；JQData/BaoStock 仅预留注册位 |
| 回测引擎 | 已完成 demo 级增强 | 支持资金、仓位、费用、滑点、曲线、信号解释、基础指标 |
| 客户报告 | 已可发布和分享 | PublishedSnapshot 固化报告内容，ShareLink 用 token 只读访问 |
| 管理端 | 已覆盖主要流程 | 可管理标的、组合、数据、策略参数、回测、paper run、快照和日志 |
| 展示端 | 已可客户演示 | 可渲染指标、K 线、交易记录、信号摘要、假设和风险披露 |
| 数据库 | 当前 SQLite，已铺迁移基线 | Alembic baseline 已建立；PostgreSQL/TimescaleDB 是后续生产化路线 |
| 自动测试 | 已覆盖主要后端流程 | 最近阶段记录为 `50 passed`；前端 admin/display build 已通过 |

可展示主线：

```text
管理端导入/拉取行情
  -> 运行 rolling_t_grid 回测
  -> 复核指标、曲线、信号、交易表和数据质量
  -> 发布不可变客户报告
  -> 展示 paper run 监控记录和失败原因
```

仍需明确的边界：

- 不接真实券商，不自动下单。
- 回测和 paper run 都是模拟，不构成收益承诺。
- JQData 账号未购买，不能展示为已可用。
- BaoStock adapter 本轮没有正式实现，只保留 provider registry 位置。
- SQLite 是当前 demo 默认数据库，PostgreSQL/TimescaleDB 尚未切换为生产默认。

## 项目地形

```text
E:/Project/quant
+-- backend/                 -> 后端业务系统：API、数据、策略、回测、快照、监控
+-- frontend-admin/          -> 内部管理端：操作员工作台
+-- frontend-display/        -> 客户展示端：只读报告页面
+-- docs/                    -> 最新交付文档、阶段记录、运行手册
+-- alembic/                 -> 数据库迁移基线
+-- data/                    -> 本地 SQLite 运行数据
+-- requirements.txt         -> Python 依赖
```

业务层次可以这样讲：

```text
[管理端]
  管股票 / 管组合 / 拉数据 / 配策略 / 跑回测 / 发报告 / 管链接 / 看日志
       |
       v
[后端 API]
  校验权限 -> 写数据库 -> 调数据源 -> 调策略回测 -> 生成快照
       |
       v
[数据库]
  instruments / bars / backtests / snapshots / share links / paper runs / logs
       |
       v
[客户展示端]
  用 token 读取已发布快照 -> 渲染只读报告
```

## 能力地图

| 能力 | 用户看到什么 | 主要模块 |
|---|---|---|
| 登录和操作记录 | 管理员登录，重要动作可追踪 | `backend/app/api/auth.py`、`backend/app/services/operation_log.py` |
| 标的和组合管理 | 股票档案、组合权重 | `backend/app/api/instruments.py`、`backend/app/api/portfolios.py` |
| 行情导入和拉取 | CSV / Tushare / AkShare 数据进入系统 | `backend/app/services/market_data.py`、`backend/app/api/market_data.py` |
| 数据质量检查 | 缺失数据、样本不足、交易日提示 | `backend/app/services/data_quality.py` |
| 策略参数配置 | rolling_t_grid 参数可保存复用 | `backend/app/strategies/registry.py`、`backend/app/api/strategy_parameter_sets.py` |
| 回测 | 指标、曲线、交易、信号解释 | `backend/app/services/backtest.py`、`backend/app/services/indicators.py` |
| 客户报告 | 发布不可变报告，生成只读链接 | `backend/app/api/snapshots.py`、`frontend-display/src/App.tsx` |
| 模拟运行 | paper run 状态、模拟信号和成交 | `backend/app/services/paper.py`、`backend/app/api/paper_runs.py` |
| 健康和迁移 | 查看数据库、schema、provider 状态 | `backend/app/api/health.py`、`backend/app/services/schema.py` |
| 管理端展示 | 集中操作工作流 | `frontend-admin/src/App.tsx`、`frontend-admin/src/api/client.ts` |

## 关键旅程一：真实行情如何变成系统里的 K 线

```text
Tushare/AkShare/CSV 原始数据
  -> provider adapter 统一字段
  -> ParsedBar 内部结构
  -> upsert_bars 写入 Bar 表
  -> DataImportTask 记录导入结果
  -> data_quality 给回测和报告提供提示
```

1. 操作员在管理端发起行情拉取，入口在 `frontend-admin/src/App.tsx`。
2. 前端调用 `backend/app/api/market_data.py`，传入标的、时间区间、频率、复权和 provider。
3. `backend/app/services/market_data.py` 根据 provider registry 选择适配器。
4. Tushare 适配器会把内部的 `symbol + exchange` 转成 Tushare 需要的 `ts_code`，例如 `600519 + SH` 转成 `600519.SH`。
5. 外部返回的数据被归一化成统一 K 线格式，再写入 `Bar` 表。
6. 导入任务会记录来源、行数、更新时间、请求参数和失败原因，方便后续演示时解释“数据从哪里来”。

## 关键旅程二：一次回测如何变成客户报告

```text
BacktestCreate 请求
  -> 找标的/组合和策略参数
  -> 读取 Bar 行情
  -> backtest service 计算资金、仓位、交易和指标
  -> BacktestRun 保存结果
  -> snapshots.publish 固化报告
  -> ShareLink 生成 token
  -> frontend-display 渲染客户报告
```

1. 管理端选择策略参数并创建回测，入口在 `backend/app/api/backtests.py`。
2. 后端读取 K 线、策略参数和数据质量信息。
3. `backend/app/services/backtest.py` 运行模拟交易逻辑，生成权益曲线、回撤曲线、仓位曲线、交易明细、指标和信号解释。
4. 回测结果保存为 `BacktestRun`，用于内部复核。
5. 管理员发布快照时，`backend/app/api/snapshots.py` 把这次结果复制成不可变的 `PublishedSnapshot`。
6. 系统创建 `ShareLink`，数据库只保存 token hash，不保存明文 token。
7. 客户打开展示端链接，`frontend-display/src/App.tsx` 读取公开快照并渲染报告。

## 关键旅程三：paper run 如何作为“模拟监控”展示

```text
操作员发起 paper run
  -> PaperRun 进入 running
  -> paper service 复用回测逻辑生成模拟信号和成交
  -> 成功则写入 summary/signals/trades
  -> 失败则写入失败原因
  -> 管理端展示状态和结果
```

paper run 的定位要讲清楚：它不是实盘，也不是自动下单。它是把策略放到“模拟运行记录”里，让客户看到系统未来可以向监控和准实时模拟方向发展。

## 信息材料和判断规则

```text
原始行情
  -> 统一 K 线
  -> 回测输入
  -> 回测结果 payload
  -> 快照 immutable_payload
  -> 客户报告图表和表格
```

| 材料 | 从哪里来 | 变成什么 | 被谁使用 |
|---|---|---|---|
| 标的档案 | 管理端录入 | `Instrument` | 行情、回测、报告 |
| K 线行情 | Tushare/AkShare/CSV | `Bar` | 回测、数据质量、图表 |
| 策略参数 | 策略注册表和管理端表单 | `StrategyParameterSet` | 回测和 paper run |
| 回测结果 | 回测服务计算 | `BacktestRun.result_payload` | 内部复核、发布快照 |
| 报告快照 | 后端发布 | `PublishedSnapshot.immutable_payload` | 客户展示端 |
| 分享链接 | 发布后生成 | `ShareLink` | 客户访问公开报告 |
| 操作日志 | 后端记录 | `OperationLog` | 审计和演示追踪 |

重要判断规则：

| 判断 | 规则来源 | 影响 |
|---|---|---|
| 用哪个数据源 | provider registry 和 API 参数 | 决定行情来自 Tushare、AkShare 或预留源 |
| 用哪种复权 | `adjust` 参数，默认 `qfq` | 影响 K 线去重、回测和报告口径 |
| 回测是否可运行 | 行情数量、策略参数、数据质量 | 决定能否生成可信报告 |
| 报告是否可变 | 快照发布机制 | 发布后客户报告内容应保持稳定 |
| token 是否安全 | 只保存 hash | 避免把分享凭证固化进数据库或文档 |

## 模块讲解

| 模块 | 文件锚点 | 客户可理解的功能 | 实现逻辑 |
|---|---|---|---|
| 应用入口 | `backend/app/main.py` | 启动后端服务 | 创建 FastAPI app，挂载路由，初始化数据库和调度器 |
| API 总路由 | `backend/app/api/router.py` | 把所有业务入口集中到 `/api` | 将 auth、market data、backtests、snapshots 等子路由统一注册 |
| 配置 | `backend/app/core/config.py` | 管理环境变量和默认配置 | 读取数据库地址、CORS、Tushare token、管理员默认信息 |
| 数据库 | `backend/app/core/database.py` | 连接和初始化本地数据 | 创建 engine/session，SQLite demo 环境下补表和种子数据 |
| 业务账本 | `backend/app/models/core.py` | 定义系统保存哪些业务对象 | 用模型描述 User、Instrument、Bar、BacktestRun、Snapshot 等 |
| 行情服务 | `backend/app/services/market_data.py` | 把外部行情变成统一 K 线 | provider adapter 负责格式转换，upsert 负责写入和去重 |
| 行情 API | `backend/app/api/market_data.py` | 给前端提供导入、拉取、查询行情能力 | 接收请求，调用行情服务，返回任务和 K 线结果 |
| 行情调度 | `backend/app/scheduler/market_data.py` | 支持定时刷新行情 | 根据 MarketDataSchedule 执行周期任务并记录结果 |
| 数据质量 | `backend/app/services/data_quality.py` | 提醒数据是否够完整 | 根据 bars、日期和交易日历生成 warning 与摘要 |
| 策略注册 | `backend/app/strategies/registry.py` | 定义系统有哪些策略和参数 | rolling_t_grid 的参数、默认值、范围由后端声明 |
| 策略参数 API | `backend/app/api/strategy_parameter_sets.py` | 保存可复用策略方案 | 校验参数后写入 StrategyParameterSet |
| 指标服务 | `backend/app/services/indicators.py` | 统一计算技术指标 | 提供 MA、EMA、MACD、RSI、BOLL 等可复用函数 |
| 回测服务 | `backend/app/services/backtest.py` | 生成策略表现和交易结果 | 读取 K 线和参数，模拟资金/仓位/交易，输出曲线、指标和解释 |
| 回测 API | `backend/app/api/backtests.py` | 创建和查询回测 | 协调标的/组合、参数、数据质量和回测结果落库 |
| 快照 API | `backend/app/api/snapshots.py` | 把回测发布成客户报告 | 生成 immutable payload、分享链接、报告摘要和公开读取接口 |
| paper 服务 | `backend/app/services/paper.py` | 生成模拟运行结果 | 复用回测输出，整理 paper_summary、signals、trades |
| paper API | `backend/app/api/paper_runs.py` | 记录模拟运行生命周期 | 管理 pending/running/succeeded/failed 状态和错误原因 |
| 健康检查 | `backend/app/api/health.py` | 看系统依赖是否正常 | 返回数据库、schema、scheduler、provider 和 public data 状态 |
| schema 检查 | `backend/app/services/schema.py` | 判断表结构是否缺失 | 支持 SQLite demo fallback 和 migration 状态检查 |
| 管理端 API 客户端 | `frontend-admin/src/api/client.ts` | 前端调用后端的统一出口 | 定义请求函数和类型，避免页面里散落 URL |
| 管理端页面 | `frontend-admin/src/App.tsx` | 内部操作工作台 | 用表单、表格和图表串起数据、策略、回测、快照、paper run |
| 展示端页面 | `frontend-display/src/App.tsx` | 客户只读报告 | 根据 URL token 加载快照，渲染指标、图表、表格和风险披露 |
| 后端测试 | `backend/tests/` | 证明主要行为不会退化 | 覆盖认证、行情、策略、回测、快照、paper run、schema 等 |

## 当前最适合对客户展示的内容

1. “从真实行情到客户报告”的闭环：Tushare 数据进入系统，回测后发布只读报告。
2. “报告不粉饰结果”的专业性：即使收益为负，也能展示真实回测、回撤、交易、数据口径和风险披露。
3. “内部工作台和客户报告分离”的产品边界：客户只看已发布内容，不参与参数修改和交易触发。
4. “后续生产化路线清晰”：数据库迁移、TimescaleDB、更多数据源、前端体验优化都有明确下一步。

## 当前薄弱点

按 demo 展示影响排序：

| 优先级 | 薄弱点 | 类型 | 展示影响 | 当前建议 |
|---|---|---|---|---|
| P0 | 展示端交互和视觉层仍偏工程化 | 前端展示 | 客户第一眼可能觉得像内部调试页 | 下一位前端 agent 优先处理 |
| P0 | 交易记录和信号解释还可以更精炼 | 前端展示/量化表达 | 长表容易淹没重点 | 默认摘要、折叠、固定高度滚动、关键交易突出 |
| P1 | 管理端流程密度较高 | 前端交互 | 现场演示时操作步骤需要更顺 | 优化数据拉取、回测、发布、复制链接的工作流 |
| P1 | 数据库仍是 SQLite 默认 | 代码/架构 | 技术客户会问数据量和部署 | 按 `database-roadmap.md` 推进 PostgreSQL/TimescaleDB |
| P1 | JQData/BaoStock 尚未实现 | 数据源 | 不能宣称多付费源已落地 | 只说 provider registry 已预留 |
| P2 | paper run 还不是准实时交易生命周期 | 量化功能 | 不适合演示成实盘监控 | 继续定位为模拟审计记录 |
| P2 | 回测撮合仍是策略样机级 | 量化功能 | 专业交易客户会追问更复杂撮合 | 后续补订单生命周期、更多成本模型、组合回测 |

## 下一阶段计划

下一阶段建议优先给新的前端 agent 执行，目标是提高 demo 展示效果，而不是再扩后端范围。

1. 客户展示端报告体验优化
   目标：让报告第一屏更像成熟投研材料。重点优化指标层级、结果解释、图表布局、长交易表、移动端和投屏宽度。

2. 管理端演示工作流优化
   目标：让操作员能更顺地完成“拉数据 -> 跑回测 -> 发布报告 -> 复制链接 -> 查看 paper run”。重点减少跳转成本、强化状态反馈、补齐空状态和失败原因。

3. 前端可靠性检查
   目标：在桌面和移动宽度下没有重叠、溢出、空白图表和 console error。重点验证 ECharts/lightweight-charts、表格滚动、token 错误页和加载态。

4. 数据库生产化
   目标：在前端 demo 稳定后，进入 PostgreSQL/TimescaleDB 实施阶段。当前先保留路线文档，不切换默认数据库。

## 工作流规范

后续仍按这个框架推进：

```text
系统分析
  -> 修改草案
  -> 人工批准
  -> 正式修改
  -> 验证
  -> 阶段记录/交接
```

系统分析必须写清：

- 当前功能状态
- 相关模块地图
- 关键流程
- 当前测试或演示证据
- 薄弱点和风险
- 本轮不处理范围

修改草案必须写清：

- 目标和用户可见效果
- 涉及文件
- API / 数据库 / 前端影响
- 测试和浏览器验证计划
- 回滚或兼容策略
- 需要人工确认的问题

正式修改只做已批准范围，不顺手扩需求。客户报告、分享链接、token、密钥、数据库迁移、真实交易相关改动都必须额外谨慎。

## 常见误解

1. 不要把展示端当成实时交易终端。它读取的是已发布快照。
2. 不要把 paper run 说成实盘交易。它是模拟运行和审计记录。
3. 不要把 Tushare 已接入等同于所有数据源都可用。JQData/BaoStock 仍是预留。
4. 不要把 SQLite demo 数据库说成生产最终方案。生产化路线是 PostgreSQL/TimescaleDB。
5. 不要把负收益报告理解成 demo 失败。它体现系统没有粉饰回测结果，下一步重点是更专业地解释结果。

## 初学者阅读路线

如果要继续理解项目，建议按这个顺序读：

1. `docs/demo-runbook.md`：先知道系统如何跑起来。
2. `docs/customer-demo-talk-track.md`：先知道怎么对客户讲。
3. `backend/app/models/core.py`：看系统有哪些业务账本。
4. `backend/app/services/market_data.py`：看真实行情如何进入系统。
5. `backend/app/services/backtest.py`：看策略结果如何生成。
6. `backend/app/api/snapshots.py`：看回测如何变成客户报告。
7. `frontend-display/src/App.tsx`：看客户报告如何渲染。
8. `frontend-admin/src/App.tsx`：看内部工作台如何组织操作。
9. `backend/tests/`：看哪些行为已有自动测试保护。

## 可继续追问

```text
项目地图
  -> 某个模块角色
      -> 某条业务旅程
          -> 某个文件锚点
              -> 函数内部逻辑
```

适合继续追问的方向：

1. 展开“客户报告从 token 到页面渲染”的完整链路。
2. 展开 `backend/app/services/backtest.py` 里回测资金和仓位如何计算。
3. 展开管理端如何把多个 API 串成演示工作流。
