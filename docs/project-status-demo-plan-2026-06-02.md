# Quant System 项目整理文档

日期：2026-06-02  
状态：项目状态梳理 + 薄弱点自查 + 长期改造执行后摘要
边界：本文档保留原系统分析口径，并追加 Phase 0 到 Phase 8 执行后的当前状态。

相关执行文档：

- [长期无人值守改造总规范](plans/2026-06-02-long-term-quant-system-upgrade.md)
- [Demo Runbook](demo-runbook.md)
- [Demo Checklist](demo-checklist.md)
- [Customer Demo Talk Track](customer-demo-talk-track.md)
- [Phase 0 Baseline Record](stage-records/phase-0-baseline.md)

## 0. 长期改造执行后状态

截至 2026-06-02，长期改造 Phase 0 到 Phase 8 已按阶段推进并记录：

| Phase | 当前状态 | 核心结果 |
|---|---|---|
| Phase 0 | verified | 固化 demo runbook、基础 smoke 和阶段记录 |
| Phase 1 | verified | 客户报告 payload、指标区、交易披露、风险说明成熟化 |
| Phase 2 | verified | 回测引擎支持资金、仓位、费用、滑点、基准和订单明细 |
| Phase 3 | verified | 管理端数据工作流默认 Tushare，支持 provider/frequency/adjust 展示 |
| Phase 4 | verified | 数据质量和交易日历 warning 进入 API、回测和报告 |
| Phase 5 | verified | 后端指标服务、信号解释、snapshot 指标字段和报告展示 |
| Phase 6 | verified | Alembic baseline、数据库路线文档、health migration 状态 |
| Phase 7 | verified | paper run 状态流转、模拟信号/成交、失败原因和管理端监控展示 |
| Phase 8 | verified | 演示 runbook、checklist、客户讲解口径和最终交付治理 |

当前最适合客户展示的主线是：

```text
管理端导入/拉取行情
  -> 运行 rolling_t_grid 回测
  -> 复核指标、信号、交易表和数据质量
  -> 发布不可变客户报告
  -> 展示 paper run 监控记录和失败原因
```

仍需明确的边界：

- 系统不接实盘券商，不做自动下单。
- 回测和 paper run 都是模拟，不构成收益承诺。
- JQData 未购买，BaoStock 未实现正式 adapter。
- SQLite 仍是默认 demo 数据库；PostgreSQL/TimescaleDB 是后续生产化路线。

## 1. 一句话定位

当前项目是一个“内部量化工作台 + 客户只读报告”的个人量化系统。内部人员在管理端完成股票、数据、策略参数、回测、快照发布和分享链接管理；客户只通过一个 token 链接查看已经发布的、不可变的策略报告。

可以把它类比成一家小型投研工作室：

```text
研究员/管理员
  -> 准备股票和行情数据
  -> 配置策略参数
  -> 运行历史回测
  -> 审核并发布报告快照
  -> 发给客户一个只读报告链接

客户
  -> 打开链接
  -> 只看已经审定的报告
  -> 不能改参数，不能触发交易
```

这个类比的边界是：系统目前还不是实盘交易系统，也不是完整投顾平台。它更像“可演示、可复核、可发布报告”的量化策略样机。

## 2. 当前项目状态

### 2.1 已验证的端到端 demo

当前最强的 demo 证据是“贵州茅台真实行情回测报告”：

| 项目 | 当前结果 |
|---|---|
| 标的 | 贵州茅台 `600519.SH` |
| 数据源 | Tushare Pro |
| 周期 | 日线 `1d` |
| 复权 | 前复权 `qfq` |
| 区间 | `2024-01-01` 到 `2026-05-29` |
| 实际入库 K 线 | 580 根，实际首日 `2024-01-02`，末日 `2026-05-29` |
| 回测 ID | `114` |
| 快照 ID | `73` |
| 报告标题 | 贵州茅台 600519.SH 真实行情回测报告 |
| 核心结果 | 累计收益 `-15.41%`，最大回撤 `-27.28%`，交易次数 `157`，胜率 `43.95%` |
| 客户报告链接 | 本地已验证，真实 share token 不写入版本库；URL 形态为 `http://127.0.0.1:<display-port>/?token=<share-token>` |

验证证据：

| 验证项 | 结果 |
|---|---|
| 后端测试 | `35 passed` |
| 展示端构建 | `npm.cmd run build` 通过 |
| 数据库 schema | `schema ok` |
| Tushare 主源状态 | 已配置，adapter 可用 |
| Playwright 页面验证 | 报告可打开，核心指标、K 线证据图、交易明细、参数假设、风险披露均渲染 |

### 2.2 项目地形图

```text
E:/Project/quant
+-- backend/                 -> 后端业务系统：接口、数据库、策略、回测、发布
+-- frontend-admin/          -> 内部管理端：管理员操作工作台
+-- frontend-display/        -> 客户展示端：只读报告页面
+-- docs/                    -> 产品设计、外部系统审计、展示研究、当前整理文档
+-- data/                    -> 本地 SQLite 数据库，运行时数据
+-- requirements.txt         -> Python 依赖，包含 FastAPI/SQLModel/Tushare 等
```

更贴近业务的层次图：

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
  instruments / bars / backtests / snapshots / share links / logs
       |
       v
[客户展示端]
  用 token 读取已发布快照 -> 渲染只读报告
```

### 2.3 模块功能和实现逻辑

#### A. 后端入口与路由

核心文件：

- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/core/database.py`
- `backend/app/core/config.py`

后端启动时会做三件事：

1. 读取配置，包括数据库地址、管理员账号、Tushare token。
2. 初始化数据库表，并做本地 SQLite 兼容升级。
3. 启动市场数据调度器。

`backend/app/api/router.py` 把各业务接口集中挂到 `/api` 下。客户或管理端看到的是 API，但实际内部会分给认证、行情、回测、快照、日志等模块处理。

#### B. 数据模型

核心文件：

- `backend/app/models/core.py`

模型可以理解为系统的“业务账本”。目前主要账本包括：

| 模型 | 给客户/业务讲法 | 当前作用 |
|---|---|---|
| `User` | 管理员账号 | 登录、记录发布人和操作人 |
| `Instrument` | 股票/标的档案 | 保存代码、交易所、名称，如 `600519 + SH + 贵州茅台` |
| `DataSourceProvider` | 数据源清单 | 记录 Tushare、JQData、AkShare、BaoStock 的角色、优先级和配置状态 |
| `Portfolio` / `PortfolioInstrument` | 固定组合 | 保存组合名称、持仓标的和权重 |
| `Bar` | K 线行情 | 保存 OHLCV，按 `标的 + 周期 + 时间 + 复权方式` 去重 |
| `DataImportTask` | 数据导入任务记录 | 记录来源、行数、失败原因、请求参数 |
| `MarketDataSchedule` | 定时数据任务 | 记录周期性拉数据任务 |
| `StrategyParameterSet` | 策略参数方案 | 保存已经归一化的策略参数 |
| `BacktestRun` | 一次回测结果 | 保存指标、权益曲线、交易记录、K 线等结果 |
| `PaperRun` | 模拟运行记录 | 保存一次手动模拟的结果摘要 |
| `PublishedSnapshot` | 客户报告快照 | 保存不可变报告内容 |
| `ShareLink` | 客户分享链接 | 只保存 token hash，不保存明文 token |
| `OperationLog` | 操作日志 | 保存谁做了什么操作 |

当前数据库改造的重点是 `Bar`、`DataImportTask`、`MarketDataSchedule` 和 `DataSourceProvider`。这让数据源、复权方式、导入行数和 provider 策略都能被追溯。

#### C. 行情数据模块

核心文件：

- `backend/app/services/market_data.py`
- `backend/app/api/market_data.py`
- `backend/app/scheduler/market_data.py`

行情模块的任务是把外部数据变成系统内部统一的 K 线。

```text
外部 provider 返回数据
  -> provider adapter 转换格式
  -> ParsedBar 统一结构
  -> upsert_bars 写入 Bar 表
  -> DataImportTask 记录导入结果
```

当前支持：

| 路径 | 状态 |
---|---|
| CSV 导入 | 已实现，适合兜底和测试 |
| AkShare | 已实现，免费兜底 |
| Tushare Pro | 已实现第一版 adapter，已用茅台真实数据验证 |
| JQData | 数据源表已预留，账号未购买，adapter 未实现 |
| BaoStock | 数据源表已预留，adapter 未实现 |

Tushare 的重要实现逻辑：

- 系统内部保存 `symbol=600519`、`exchange=SH`。
- Tushare adapter 转成 `600519.SH`。
- 后端 API 仍接受当前日期格式，adapter 内部转换成 Tushare 需要的格式。
- 日线和分钟线统一优先走 `ts.pro_bar`。
- 默认使用 `qfq`，但数据库允许 `空/qfq/hfq` 并存。

#### D. 策略参数模块

核心文件：

- `backend/app/strategies/registry.py`
- `backend/app/api/strategy_parameter_sets.py`

系统现在有一个内置策略：`rolling_t_grid`，也就是滚动做 T / 网格策略。

它的参数不是写死在前端，而是由后端策略注册表声明：

| 参数 | 业务含义 |
---|---|
| `grid_percent` | 价格变化超过多少百分比触发买卖 |
| `base_position_percent` | 基础仓位比例 |
| `trade_position_percent` | 每次网格交易使用的仓位比例 |
| `enable_ma_filter` | 是否启用均线过滤 |
| `ma_window` | 均线窗口 |

管理端根据策略元数据生成参数表单，后端负责校验默认值、范围、类型。这一点很重要：前端只是填表，真正的规则归后端管。

#### E. 回测模块

核心文件：

- `backend/app/services/backtest.py`
- `backend/app/api/backtests.py`

回测模块读取已经入库的 K 线和策略参数，然后生成结果对象。

```text
BacktestCreate 请求
  -> 找标的/组合
  -> 按 frequency + adjust 读取 Bar
  -> 读取 StrategyParameterSet
  -> run_single_instrument_backtest 或 run_portfolio_backtest
  -> 保存 BacktestRun
```

当前回测结果包括：

- 核心指标：bar 数、交易次数、累计收益、最大回撤、胜率、盈亏比占位。
- 图表数据：权益曲线、基准曲线、回撤曲线、K 线、买卖点、仓位曲线。
- 交易表：模拟买卖时间、方向、价格、变化比例。
- 风险披露文本。

要注意：现在回测逻辑偏简化。它更适合 demo 和流程展示，还不是严谨交易撮合引擎。

#### F. 快照与客户报告模块

核心文件：

- `backend/app/api/snapshots.py`
- `frontend-display/src/App.tsx`
- `frontend-display/src/App.css`

快照模块负责把一次回测结果变成客户可看的“不可变报告”。

```text
管理员选择一个成功回测
  -> 发布快照 PublishedSnapshot
  -> 复制 backtest 结果和报告元数据
  -> 创建 ShareLink
  -> 返回一次性明文 share_token
  -> 客户打开 token 链接
  -> display 前端读取公开快照并渲染
```

客户报告展示端目前包含：

1. 报告标题和只读快照状态。
2. 累计收益、最大回撤、胜率、交易次数等核心指标。
3. 策略权益、基准和回撤图。
4. K 线、均线、成交量、买卖点图。
5. 仓位曲线。
6. 模拟交易记录表。
7. 参数与回测假设。
8. 风险披露和数据质量说明。

客户报告是只读的。客户不能改参数，也不会触发新的回测或交易。

#### G. 管理端模块

核心文件：

- `frontend-admin/src/App.tsx`
- `frontend-admin/src/api/client.ts`

管理端是一个操作工作台，主要功能是：

- 登录。
- 管理标的和组合。
- 导入或拉取行情。
- 查看数据完整性。
- 配置策略参数。
- 发起回测。
- 发起模拟运行。
- 发布展示快照。
- 创建或撤销分享链接。
- 查看操作日志。

管理端当前功能面比较全，但部分表单还没有完全跟上后端新字段，例如 provider 选择、adjust 过滤、Tushare 主源切换还没有做成完整前端控件。

#### H. 健康检查与测试

核心文件：

- `backend/app/api/health.py`
- `backend/app/services/schema.py`
- `backend/tests/`

健康检查会报告：

- 数据库是否可用。
- schema 是否缺表/缺列。
- 调度器是否运行。
- 数据源 provider 是否注册和配置。
- Tushare 主源是否配置。

测试目前覆盖：

- 登录和日志。
- 标的、组合。
- 行情导入、公共数据 provider 合约。
- 回测、组合回测。
- 模拟运行。
- 快照发布、分享链接、撤销。
- schema 健康检查。

当前验证结果是 `34 passed`。

## 3. 关键业务旅程 walkthrough

### 3.1 从真实行情到客户报告

```text
Tushare 真实数据
  -> market_data.fetch_public_bars
  -> Bar 表保存 600519.SH 日线 qfq
  -> backtests.create / backtest service
  -> BacktestRun 保存指标和图表数据
  -> snapshots.publish
  -> PublishedSnapshot 固化报告内容
  -> ShareLink 生成 token
  -> frontend-display 读取 public snapshot
  -> 客户看到报告
```

对应代码锚点：

| 步骤 | 入口 |
|---|---|
| 拉取 Tushare 数据 | `backend/app/services/market_data.py` |
| 写入 K 线 | `upsert_bars` |
| 创建回测 | `backend/app/api/backtests.py` |
| 运行策略 | `backend/app/services/backtest.py` |
| 发布快照 | `backend/app/api/snapshots.py` |
| 客户读取报告 | `GET /api/public/snapshots/{share_token}` |
| 页面渲染报告 | `frontend-display/src/App.tsx` |

### 3.2 数据材料如何变化

```text
Tushare DataFrame
  -> rows_from_provider_result
  -> normalize_tushare_row
  -> ParsedBar
  -> Bar 数据库行
  -> BacktestRun.result_payload
  -> PublishedSnapshot.immutable_payload
  -> 客户报告图表和表格
```

这个流向是当前项目最重要的可信度来源：客户看到的不是前端临时计算的结果，而是后端已经保存和发布的快照。

## 4. 当前薄弱点自查

以下按“影响 demo 展示效果优先”排序。

### 4.1 P0：影响客户第一眼信任的薄弱点

#### 4.1.1 回测指标还太薄

类型：量化层功能薄弱点  
影响：客户会问“为什么只有累计收益、回撤、胜率？有没有年化、夏普、波动率、盈亏比、手续费、滑点？”

当前问题：

- `annualized_return` 前端有位置，但后端未计算。
- `sharpe_ratio` 前端类型中预留，但后端未填。
- `profit_loss_ratio` 当前为 `0`，不是真实盈亏比。
- 没有波动率、Calmar、收益回撤比、持仓时间、换手率。
- 没有手续费、滑点、成交模型参数。

展示影响：

- 客户报告看起来像“能跑通”，但不像“成熟回测报告”。
- 茅台真实回测结果为负，反而更需要完整风险指标来体现专业度。

#### 4.1.2 当前策略执行逻辑偏演示

类型：量化层功能薄弱点  
影响：懂交易的客户会追问“仓位怎么变化？买卖数量怎么计算？是否考虑资金占用？”

当前问题：

- 策略权益曲线目前主要跟随标的收盘价变化，并不是真正逐笔资金、持仓、现金流模拟。
- `trade_position_percent` 参数声明存在，但回测引擎没有真正用它计算仓位变化。
- `enable_ma_filter` 和 `ma_window` 参数已经进入参数集，但回测服务中未真正应用均线过滤逻辑。
- 买卖点来自价格网格变化，不等同于完整交易撮合。

展示影响：

- 报告视觉上完整，但策略逻辑解释时容易被问穿。
- 如果客户理解为“这是完整交易系统”，会产生误解。

#### 4.1.3 客户报告交易明细过长

类型：前端展示薄弱点  
影响：页面滚动很长，客户会被 157 笔交易记录淹没。

当前问题：

- 模拟交易记录表一次性展示全部交易。
- 没有分页、折叠、滚动容器或“展示最近 N 笔”。
- K 线证据图已经足够表达交易点，交易表应作为辅助而不是占据大量页面长度。

展示影响：

- 客户报告像“后台明细表”而不是“客户汇报材料”。
- 手机端或投屏展示时体验会明显下降。

### 4.2 P1：影响演示稳定性的薄弱点

#### 4.2.1 管理端未完全接上新数据源能力

类型：前端展示 / 工作流薄弱点  
影响：真实 Tushare 已接入后端，但管理端仍像旧版 AkShare 流程。

当前问题：

- `frontend-admin/src/api/client.ts` 的类型还没有同步 `provider`、`adjust`、`DataImportTask` 新字段。
- 前端表单目前仍倾向显示 AkShare，而不是主源 Tushare。
- 后端支持 `provider` 参数，但管理端 provider 切换体验不完整。

展示影响：

- 如果现场需要从管理端演示“选择 Tushare 拉茅台”，可能不够顺。
- 更稳的 demo 方式是提前准备好数据和报告，只展示结果。

#### 4.2.2 数据库迁移还是本地兼容升级，不是正式迁移系统

类型：代码层架构薄弱点  
影响：demo 可用，但生产部署或多环境升级时风险偏高。

当前问题：

- 项目没有 Alembic 或正式 migration 版本管理。
- SQLite 兼容升级逻辑在 `backend/app/services/schema.py`，适合本地 demo，但不是长期生产方案。
- 还没有 PostgreSQL/TimescaleDB 的正式落地脚本。

展示影响：

- 客户一般不会直接问迁移系统，但技术评审会问“以后数据量变大怎么办？”
- 回答应是：当前本地 demo 使用 SQLite，下一阶段进入 PostgreSQL/TimescaleDB 规划。

#### 4.2.3 数据质量检查还不是交易日历级别

类型：量化层 / 数据层薄弱点  
影响：客户可能问“缺少交易日怎么办？停牌怎么办？”

当前问题：

- 当前完整性检查按时间间隔估算，不基于 A 股交易日历。
- 没有对停牌、节假日、半日交易、异常成交量做专项标记。
- Tushare 交易日历已在需求中提出，但第一批还没实现。

展示影响：

- 茅台日线 demo 样本足够，但不能声称已经做了完整交易日历审计。

### 4.3 P2：影响专业扩展性的薄弱点

#### 4.3.1 指标层还没有成为后端一等能力

类型：量化层功能薄弱点  
当前状态：

- 客户报告前端会计算/补充 MA、MACD 展示。
- 后端没有统一的指标计算和缓存层。
- 快照里没有完整保存指标计算参数和版本。

展示影响：

- 视觉上已有 K 线和指标，但技术上还不能说“指标体系已平台化”。

#### 4.3.2 Paper simulation 还没有独立信号/交易生命周期

类型：量化层 / 数据模型薄弱点  
当前状态：

- `PaperRun` 保存模拟运行摘要。
- 没有独立 `PaperSignal`、`PaperTrade`、订单状态、成交状态。

展示影响：

- 不影响本次客户报告 demo。
- 如果要演示“准实时模拟交易”，会显得浅。

#### 4.3.3 客户报告缺少“解释层”

类型：前端展示薄弱点  
当前状态：

- 报告有风险披露和方法假设。
- 还没有自动生成的“策略表现摘要”和“为什么这段表现较弱”的解释。
- 没有把负收益 demo 转化为专业叙述，例如“策略在单边下行阶段暴露的适配问题”。

展示影响：

- 当前茅台结果为负，需要解释层帮助客户理解：这不是失败，而是真实回测揭示策略适配边界。

## 5. 下一阶段计划，按展示效果优先

### Phase 1：让客户报告更像成熟投研报告

目标：优先提升 demo 观感和可解释性。

修改草案：

1. 后端补齐基础回测指标：
   - 年化收益。
   - 年化波动率。
   - Sharpe。
   - Calmar。
   - 收益回撤比。
   - 真实盈亏比。
   - 平均盈利、平均亏损。
   - 持仓天数/交易频率。
2. 报告快照增加 `report_summary`：
   - 一句话说明策略表现。
   - 一句话说明主要风险。
   - 一句话说明数据源和假设。
3. 客户报告交易明细改为滚动/折叠：
   - 默认展示最近 20 笔或关键交易。
   - 提供“展开全部”。
   - 表格区域固定高度滚动。
4. 报告顶部增加“结果解读”：
   - 对负收益也用专业语言解释。
   - 明确“该策略在本区间未跑赢持有或未达到目标”的状态。

建议优先级：最高。  
原因：客户第一眼看到的是报告，不是代码。

### Phase 2：让策略回测逻辑更经得起追问

目标：把当前演示型回测升级为更真实的规则回测。

修改草案：

1. 在回测引擎中真正使用：
   - `base_position_percent`
   - `trade_position_percent`
   - `enable_ma_filter`
   - `ma_window`
2. 引入资金账户模拟：
   - 初始现金。
   - 持仓市值。
   - 可用现金。
   - 每次买卖数量。
   - 交易后权益。
3. 引入手续费和滑点参数：
   - 默认可设为 0，但必须进入报告假设。
   - 后续可在管理端配置。
4. 输出更清晰的交易表：
   - signal_time。
   - side。
   - price。
   - quantity。
   - cash_after。
   - position_after。
   - fee。
   - reason。

建议优先级：高。  
原因：客户如果深入问策略逻辑，这部分决定可信度。

### Phase 3：让管理端可以顺滑演示真实数据源

目标：把后端 Tushare 能力显性化到管理端。

修改草案：

1. 管理端公共数据拉取表单增加 provider 选择：
   - 默认 Tushare。
   - 可选 AkShare。
   - JQData/BaoStock 显示为预留或禁用。
2. 表单增加 adjust：
   - 空复权。
   - qfq。
   - hfq。
3. 数据任务列表展示：
   - provider。
   - adjust。
   - rows_imported。
   - rows_updated。
   - request_params 简要信息。
4. 行情查询和完整性检查支持 adjust。

建议优先级：中高。  
原因：这让现场演示从“我用脚本准备好了”升级为“系统内可以操作”。

### Phase 4：数据库与部署正式化

目标：从本地 demo 走向可部署系统。

修改草案：

1. 引入 Alembic migration：
   - 为当前 schema 生成 baseline。
   - 之后所有表结构修改走 migration。
2. 写 PostgreSQL/TimescaleDB 部署方案：
   - 本地 SQLite 保留作开发。
   - 生产数据迁移到 PostgreSQL/TimescaleDB。
3. 对 K 线表做生产级设计：
   - 按周期/标的/时间优化索引。
   - 明确 qfq/hfq/未复权存储策略。
   - 明确 provider 原始字段是否归档。
4. 增加数据备份和初始化说明。

建议优先级：中。  
原因：短期不影响客户报告 demo，但影响后续正式交付。

### Phase 5：指标、监控和准实时模拟

目标：从报告系统继续扩展成投研工作台。

修改草案：

1. 后端指标层：
   - MA。
   - MACD。
   - RSI。
   - BOLL。
   - 指标参数和版本进入快照。
2. Watchlist / Monitor：
   - 管理端维护关注标的。
   - 定时扫描策略信号。
   - 内部提示，不对客户展示为实时信号。
3. PaperSignal / PaperTrade：
   - 独立记录模拟信号和模拟成交。
   - 不再只把结果塞进 `PaperRun.config`。

建议优先级：中低。  
原因：这是产品扩展，不是当前客户报告 demo 的最大短板。

## 6. 优化后的工作流

以后每次正式改造都按这个框架走。

```text
系统分析
  -> 修改草案
  -> 人工批准
  -> 正式修改
  -> 验证
  -> 复盘记录
```

### 6.1 系统分析

目标：先弄清楚“现在是什么”，避免一上来就改。

必须输出：

1. 当前功能状态。
2. 相关模块地图。
3. 已有代码锚点。
4. 当前数据/测试证据。
5. 风险和薄弱点。
6. 不做什么。

模板：

```text
系统分析：[主题]

1. 当前状态
2. 相关模块
3. 关键流程
4. 当前证据
5. 薄弱点
6. 本轮不处理范围
```

### 6.2 修改草案

目标：提出方案，但不直接进入正式修改。

必须输出：

1. 修改目标。
2. 用户可见效果。
3. 涉及文件。
4. 数据库影响。
5. API 影响。
6. 前端影响。
7. 测试计划。
8. 回滚或兼容策略。
9. 待人工确认的问题。

模板：

```text
修改草案：[主题]

目标：
- ...

计划改动：
- 后端：
- 数据库：
- 前端：
- 测试：

风险：
- ...

验收标准：
- ...

等待人工批准：
- 批准后才进入正式修改。
```

### 6.3 人工批准

目标：在进入正式修改前，让人确认范围和优先级。

批准口径建议：

```text
批准 Phase X，按草案执行。
本轮不做：...
验收标准：...
```

如果需求变化，应回到“修改草案”，不要直接改代码。

### 6.4 正式修改

目标：只实现已批准范围。

执行规则：

1. 不顺手重构无关模块。
2. 不覆盖用户已有未提交改动。
3. 数据库修改必须有迁移或兼容策略。
4. 后端逻辑要有测试。
5. 前端展示要浏览器验证。
6. 客户报告相关改动要保留旧快照兼容。

### 6.5 验证

每次正式修改至少给出：

| 类型 | 验证 |
|---|---|
| 后端 | `pytest backend/tests` |
| 前端 | `npm.cmd run build` |
| 数据库 | schema check 或 migration check |
| 展示页 | Playwright 打开实际页面 |
| 关键 demo | 用真实或固定样例复跑 |

### 6.6 复盘记录

正式修改后新增一段：

```text
完成内容：
- ...

验证结果：
- ...

剩余风险：
- ...

下一步建议：
- ...
```

## 7. 下一阶段推荐先走的修改草案

推荐先做 Phase 1：客户报告成熟度提升。

### 草案：客户报告成熟度提升

目标：

让当前“贵州茅台真实行情回测报告”从“能跑通”升级为“更像成熟投研汇报”。

本轮建议改动：

1. 后端补指标：
   - `annualized_return`
   - `annualized_volatility`
   - `sharpe_ratio`
   - `calmar_ratio`
   - `return_drawdown_ratio`
   - `average_win`
   - `average_loss`
   - `profit_loss_ratio`
2. 快照 payload 补 `report_summary`：
   - `performance_summary`
   - `risk_summary`
   - `method_summary`
3. 展示端优化：
   - 顶部增加“报告解读”。
   - 交易明细表改成固定高度滚动。
   - 默认突出最近/关键交易，而不是全量铺满页面。
4. 测试：
   - 后端指标计算测试。
   - 快照 payload 兼容测试。
   - 展示端 build。
   - Playwright 打开茅台报告。

不做：

- 不引入新策略。
- 不做实盘交易。
- 不做 JQData/BaoStock adapter。
- 不做 PostgreSQL/TimescaleDB 迁移。

验收标准：

1. 茅台报告顶部能解释负收益和最大回撤。
2. 核心指标比现在更完整。
3. 交易表不再拖长整个页面。
4. 旧快照仍能打开。
5. 后端测试和展示端构建通过。

等待人工批准：

如果批准，下一轮进入正式修改；如果要优先改管理端 Tushare 操作流，则改走 Phase 3。

## 8. 常见误解提醒

1. 这个系统不是实盘交易系统。  
   当前定位是回测、模拟、发布报告。

2. 客户报告不是实时页面。  
   它读取的是已发布快照，快照发布后应保持稳定。

3. 前端不是策略计算引擎。  
   前端只渲染后端快照数据，不负责决定买卖逻辑。

4. 真实数据源接入不等于量化能力成熟。  
   Tushare 已经能拉真实数据，但策略回测、指标和交易模型还需要继续加强。

5. 当前负收益结果不是坏事。  
   它说明系统没有粉饰回测结果。下一阶段要做的是补全解释层和风险指标，让负结果也能被专业表达。

## 9. 给客户讲解时的推荐话术

可以这样讲：

> 这个系统目前已经打通了从真实行情数据、策略回测、报告发布到客户只读展示的完整链路。我们用贵州茅台的 Tushare 真实日线数据做了一个演示报告，结果不是人为挑选的漂亮收益，而是完整展示策略在该区间下的真实表现，包括负收益、最大回撤、交易记录和风险披露。下一阶段会优先补齐更专业的回测指标、手续费滑点、策略解释层和报告交互细节，让它从可演示样机进一步接近正式投研报告系统。

## 10. 初学者阅读路线

如果要继续理解项目，建议按这个顺序读：

1. `docs/quant-system-prd-and-architecture.md`  
   先理解产品目标和边界。

2. `backend/app/models/core.py`  
   看系统有哪些业务账本。

3. `backend/app/services/market_data.py`  
   看真实行情如何进入系统。

4. `backend/app/services/backtest.py`  
   看策略回测目前怎么生成结果。

5. `backend/app/api/snapshots.py`  
   看回测如何变成客户报告快照。

6. `frontend-display/src/App.tsx`  
   看客户报告如何渲染。

7. `backend/tests/`  
   看哪些功能已有自动测试保护。
