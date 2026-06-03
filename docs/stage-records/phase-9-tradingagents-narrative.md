# Phase 9 - TradingAgents Client Narrative

日期：2026-06-03

## 目标

在不改变现有量化策略、回测指标、模拟成交和快照不可变机制的前提下，为客户展示报告增加一层已审核、可解释、可审计的投研叙事。

## 已完成

- 新增 `NarrativeRun` 持久化模型和 Alembic 迁移。
- 新增保守量化评级服务：`positive`、`neutral`、`cautious`。
- 新增 A 股 ticker 映射：`SH/SSE -> .SS`，`SZ/SZSE -> .SZ`。
- 新增叙事输入摘要构建，支持单标的和组合 Top 3 权重覆盖。
- 新增 TradingAgents provider 抽象和 mock provider。
- 新增叙事状态机：
  - pending
  - running
  - succeeded
  - degraded
  - failed
  - reviewed
- 新增管理端 Narrative API：
  - 配置查询
  - 生成
  - 查询当前回测叙事
  - 保存草稿
  - 降级确认
  - 审核通过
  - 撤回审核
  - 重新生成
- 发布 snapshot 时自动包含当前 reviewed narrative。
- 公共 snapshot payload 只包含客户安全字段。
- 管理端新增 AI 投研叙事审核工作区。
- 客户展示端新增叙事渲染，位置为图表之后、交易记录之前。
- 新增 TradingAgents smoke 脚本和 runbook。

## 安全边界

- 客户侧不展示 TradingAgents 名称。
- 客户侧不展示 raw provider suggestion。
- 客户侧不展示 degraded 状态或原因。
- 客户侧不展示 reviewer、review time、analysis date。
- 客户侧不展示 quant rating 输入或规则细节。
- TradingAgents 仅作为叙事 provider，不改写量化结果。
- 已发布 snapshot 不会被后续叙事重新生成影响。

## 验证

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -v
```

结果：95 passed。

管理端：

```powershell
cd frontend-admin
npm.cmd run build
```

结果：通过。Vite 仅提示 chunk size warning。

客户展示端：

```powershell
cd frontend-display
npm.cmd run build
```

结果：通过。Vite 仅提示 chunk size warning。

浏览器基础检查：

- 管理端 dev server：`http://127.0.0.1:5183` 返回 200，登录页可渲染。
- 展示端 dev server：`http://127.0.0.1:5184` 返回 200，无 token 时展示“报告不可用”，符合预期。

## 未执行项

真实 TradingAgents smoke 尚未在本阶段执行。原因：

- 需要当前分支后端以新代码启动。
- 需要安装 `tradingagents==0.2.5` 及其依赖。
- 需要调用 DeepSeek、yfinance/Alpha Vantage 等外部服务，耗时和稳定性取决于网络与额度。

执行命令：

```powershell
.\scripts\run_tradingagents_smoke.ps1
```

可接受结果：

- `succeeded`
- `degraded`，且管理端可确认后审核

## 后续建议

- 在真实 smoke 通过后，为 smoke/test snapshot 使用明确测试标题。
- 根据实际 TradingAgents 输出质量微调模块归一化逻辑。
- 如 chunk size warning 影响加载体验，再评估 ECharts 或 AntD 的按需拆包。
