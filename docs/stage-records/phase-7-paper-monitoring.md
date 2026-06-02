# Phase 7 模拟交易与监控成熟化记录

日期：2026-06-02

阶段：Phase 7 模拟交易与监控成熟化
状态：verified

## 1. 执行范围

本阶段把 paper run 从单次结果记录升级为可审计的模拟监控记录：

- `PaperRun` 增加 `started_at`、`finished_at`。
- 成功和失败的 paper run 都会落库。
- `config.state_history` 记录 pending、running、succeeded/failed 状态流转。
- `config.paper_signals` 记录本次模拟产生的信号事件。
- `config.paper_trades` 记录本次模拟成交。
- `config.error` 记录失败类型和失败原因。
- 管理端模拟运行表显示最新信号、决策、模拟成交数、失败原因和结束时间。
- 管理端展开行显示状态流转、信号说明和监控数据摘要。

## 2. 修改文件

- `backend/app/models/core.py`
- `backend/app/api/paper_runs.py`
- `backend/app/services/paper.py`
- `backend/app/services/schema.py`
- `backend/tests/test_paper_runs.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_schema_health.py`
- `alembic/versions/20260602_000002_paper_run_monitoring.py`
- `frontend-admin/src/api/client.ts`
- `frontend-admin/src/App.tsx`
- `frontend-admin/src/App.css`
- `docs/plans/2026-06-02-long-term-quant-system-upgrade.md`
- `docs/stage-records/phase-7-paper-monitoring.md`

## 3. 完成内容

- paper run 请求通过基础校验后先创建 pending 记录，再进入 running。
- 回测服务抛出缺失 K 线等错误时，paper run 更新为 failed，并保留错误原因。
- 成功运行时，paper run 更新为 succeeded，并写入 metrics、result_payload、paper_summary、paper_signals、paper_trades。
- `paper_summary` 继承 Phase 5 的 signal_summary，包含 latest_signal、latest_decision、latest_reason、signal_count、simulated_trade_count。
- Alembic 新增 `20260602_000002`，为 `paperrun` 增加 `started_at` 和 `finished_at`。
- SQLite fallback 同步支持历史开发库补这两个字段。
- 管理端失败后会刷新 paper run 列表，失败记录不会只停留在错误提示里。

## 4. 验证结果

- 目标后端测试：`.venv\Scripts\python.exe -m pytest backend\tests\test_paper_runs.py backend\tests\test_migrations.py backend\tests\test_schema_health.py`，结果 `6 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `50 passed`。
- 管理端构建：`cd frontend-admin; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 管理端浏览器 smoke：使用当前代码后端 `8004` 和管理端 `5186` 创建一条 succeeded paper run 和一条 failed paper run；表格显示“决策”“模拟成交”“失败原因”，展开行显示“状态流转”“信号说明”“监控数据”，无应用 console error。

## 5. 已知说明

- 本阶段仍是模拟交易，不接券商 API，不下真实订单。
- PaperSignal/PaperTrade 第一版使用 JSON payload 固化在 `PaperRun.config` 中；后续如果需要复杂查询，可再拆成独立表。
- 本阶段没有实现失败自动重试，只记录失败状态和原因。

## 6. 停止条件检查

当前未触发停止条件：

- 未接入实盘交易。
- 未引入自动下单。
- 未要求实时行情。

## 7. 下一阶段提示

Phase 8 将进入演示打包与交付治理。重点是复跑完整 demo、更新 checklist、整理客户讲解口径和交付边界。
