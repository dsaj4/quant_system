# 真实策略运行与分享报告 Agent 工作规范

日期：2026-06-03
适用范围：下一位专门负责“真实运行策略、观察回测效果、生成分享报告”的 agent
目标：在现有量化系统上复跑真实或固定样例数据，运行策略回测，客观记录效果，发布只读报告，并把可演示结果交给用户。

## 接手前先读

1. `docs/demo-runbook.md`
2. `docs/demo-checklist.md`
3. `docs/customer-demo-talk-track.md`
4. `docs/project-status-demo-plan-2026-06-02.md`
5. `docs/stage-records/phase-8-delivery.md`
6. `docs/frontend-agent-work-spec.md`

重点源码：

- `backend/app/services/market_data.py`
- `backend/app/services/backtest.py`
- `backend/app/services/data_quality.py`
- `backend/app/services/indicators.py`
- `backend/app/api/backtests.py`
- `backend/app/api/snapshots.py`
- `backend/app/api/paper_runs.py`
- `frontend-admin/src/api/client.ts`
- `frontend-admin/src/App.tsx`
- `frontend-display/src/App.tsx`

## 工作定位

这个 agent 的任务不是继续开发新功能，而是像演示操作员一样把系统真正跑一遍：

```text
启动/确认服务
  -> 检查数据源和数据库
  -> 拉取或复用行情
  -> 选择策略参数
  -> 运行回测
  -> 分析回测效果
  -> 发布 snapshot 和 share link
  -> 打开客户报告验证
  -> 输出非敏感运行摘要
```

重点是“真实、可复核、不粉饰”。如果回测结果不好，也要如实呈现并解释策略适配边界。

## 必须遵守的边界

- 不接真实券商，不做自动下单。
- 不把 paper run 或回测描述成实盘交易。
- 不承诺收益，不暗示历史结果代表未来收益。
- 不在文档、commit、日志、截图说明里写入 Tushare token、明文 share token、账号密码或私有链接。
- 不提交本地数据库、`.env`、日志、截图、`.venv`、`node_modules`。
- 不重置、清空、删除当前 SQLite 数据库。
- 不改后端 API、数据表、回测规则或前端契约；如果发现必须改代码，先写修改草案并等待批准。
- 不为了得到更好结果而随意改区间、改参数或挑选样本；任何调整都要记录原因。

## 当前工作区注意事项

接手时先执行：

```powershell
git status --short --branch
```

如果看到前端相关文件已有未提交改动，不要覆盖。它们可能来自另一个前端重构 agent。真实运行 agent 可以使用这些页面做演示验证，但除非用户明确批准，不要编辑它们。

## 推荐使用的技能

- `browser:control-in-app-browser`：打开管理台和展示端，验证报告、图表、控制台错误。
- `diagnose`：当服务启动、数据源、回测或报告生成失败时使用系统化诊断。
- `beginner-code-logic-reader`：需要解释某个流程或模块时使用。
- `grill-me`：如果用户要更换标的、区间、策略或验收口径，用于对齐边界。
- `handoff`：完成后如需交给下一个 agent，写临时目录交接文档。

## 默认运行方案

如果用户没有另行指定，默认采用：

| 项 | 默认值 |
|---|---|
| 标的 | 贵州茅台 `600519.SH` |
| 数据源 | Tushare Pro |
| 频率 | 日线 `1d` |
| 复权 | 前复权 `qfq` |
| 策略 | `rolling_t_grid` |
| 数据区间 | 优先使用系统中已有 Moutai demo 区间；如需新增拉取，使用最小必要区间 |
| 报告 | 发布新的 `PublishedSnapshot` 并创建 share link |

如果 Tushare 不可用，才切换到 runbook 里的固定 CSV demo。切换原因必须写清楚。

## 执行流程

### 1. 启动前检查

执行：

```powershell
git branch --show-current
git status --short
```

确认：

- 当前分支通常应为 `codex/long-term-quant-upgrade`。
- 没有准备误提交的密钥、数据库、截图或日志。
- `.env` 或 `backend/.env` 可以本地存在，但不能提交。
- 如果有其他 agent 的未提交前端改动，不要覆盖。

### 2. 后端健康检查

按 `docs/demo-runbook.md` 启动后端，然后检查：

- `/api/health` 中 database 是否正常。
- schema/migration 状态是否正常。
- Tushare 是否 configured。
- provider registry 是否包含 Tushare、AkShare、JQData/BaoStock 预留状态。

如果 Tushare 未配置：

- 不要向用户索要或打印已有 token。
- 只说明当前进程未读到本地配置。
- 可以改用固定 CSV 路径，或等待用户确认提供/修复本地配置。

### 3. 前端启动与页面确认

按 runbook 启动：

```powershell
cd frontend-admin
npm.cmd run dev
```

```powershell
cd frontend-display
npm.cmd run dev
```

用浏览器确认：

- 管理台能打开并登录。
- 展示端能加载公开报告接口。
- 控制台没有新增应用级 error。

如果前端正处于重构未提交状态，优先使用现有页面完成操作；如果页面不可用，可改用后端 API 完成运行，但要说明原因。

### 4. 行情准备

优先真实数据：

1. 确认或创建 `600519.SH` 标的。
2. 使用 Tushare、`1d`、`qfq` 拉取行情。
3. 记录非敏感信息：标的、区间、frequency、adjust、provider、导入行数、更新行数、任务 ID。
4. 检查 data quality warning。

兜底 CSV：

1. 按 `docs/demo-runbook.md` 的 CSV 示例导入。
2. 记录这是离线固定样例，不是真实行情。
3. 不把 CSV 结果包装成真实市场表现。

### 5. 策略和回测

选择或创建 `rolling_t_grid` 参数集。运行回测后必须记录：

- backtest ID
- instrument 或 portfolio
- strategy name
- parameter set ID 或参数摘要
- bar 数量
- 数据区间
- 累计收益
- 最大回撤
- 胜率
- 交易次数
- 年化收益、波动、Sharpe、Calmar 等如 payload 中存在则记录
- data quality warning
- 关键 signal summary

分析要求：

- 先讲结果，再讲原因。
- 收益为负时，不说“失败”，而是说明该策略在该区间的适配问题、趋势环境和风险暴露。
- 不改参数追求漂亮结果；如用户要求比较参数，必须把每组参数和结果都记录。

### 6. 发布分享报告

回测成功后：

1. 发布 `PublishedSnapshot`。
2. 创建 `ShareLink`。
3. 打开展示端 URL 验证报告。
4. 检查核心指标、图表、交易表、假设、风险披露、数据质量是否渲染。
5. 浏览器 console 不应有新增应用级 error。

安全要求：

- 明文 share token 可以在当前聊天中临时提供给用户打开，但不能写入仓库文档或 commit。
- 如果要写运行记录，只写 snapshot ID、backtest ID、标的、区间、指标摘要，不写 token。

### 7. 可选 paper run

如果用户要求展示模拟运行：

- 运行一次成功 paper run。
- 记录状态流转、latest signal、simulated trades。
- 可再运行一次失败场景验证失败原因，但不要污染客户报告主线。
- 明确 paper run 是模拟，不是实盘。

## 输出格式

最终回复至少包含：

- 数据源和标的：例如 Tushare / `600519.SH` / `1d` / `qfq`。
- 数据区间和导入行数。
- backtest ID、snapshot ID；share link 如用户需要可以给出。
- 核心指标摘要。
- 对回测效果的客观解释。
- 报告页面验证结果。
- 未完成项或异常：例如 Tushare 未配置、前端重构中、图表异常、数据质量 warning。

不要在最终回复中贴出 API token、数据库密钥或不必要的私有凭据。

## 验证命令

优先执行：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

如本轮只做操作不改代码，可以不跑完整测试，但要说明原因。若生成新报告，至少做浏览器验证。

前端 build：

```powershell
cd frontend-admin
npm.cmd run build
```

```powershell
cd frontend-display
npm.cmd run build
```

如果当前有另一个前端 agent 的未提交重构导致 build 不稳定，不要擅自修复它；记录现象并继续用后端 API 或已可用页面完成报告生成。

## 失败处理

常见失败优先按这个顺序排查：

1. 服务端口是否正确。
2. 当前后端是否连接了预期 SQLite 数据库。
3. `/api/health` 是否显示 schema 和 provider 正常。
4. Tushare token 是否被当前后端进程读取。
5. 标的代码和 exchange 是否能转换为 `ts_code`。
6. date/frequency/adjust 是否为后端支持值。
7. Bar 数据是否足够回测。
8. snapshot/share link 是否属于当前数据库。
9. 展示端 API base URL 是否指向当前后端。

处理失败时先诊断，不要直接删库、重置数据或改业务代码。
