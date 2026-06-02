# Phase 5 指标层和策略解释记录

日期：2026-06-02

阶段：Phase 5 指标层和策略解释
状态：verified

## 1. 执行范围

本阶段把指标计算和策略信号解释从隐式逻辑中抽出，固化到回测结果和客户报告快照中：

- 新增后端统一指标服务，覆盖 MA、EMA、MACD、RSI、BOLL。
- 回测 payload 写入 `technical_indicators`、`indicator_summary`、`signal_events`、`signal_summary`。
- MA 过滤改为调用指标服务，避免回测服务内散落均线计算。
- snapshot 顶层透出指标和信号摘要，客户报告不需要重新计算核心指标。
- 展示端报告显示最新信号、信号决策、执行/拦截数和规则参数。
- 管理端回测列表和复核面板显示信号概览，便于 demo 后台讲解。

## 2. 修改文件

- `backend/app/services/indicators.py`
- `backend/app/services/backtest.py`
- `backend/app/api/snapshots.py`
- `backend/tests/test_indicators.py`
- `backend/tests/test_backtests.py`
- `backend/tests/test_snapshots.py`
- `frontend-display/src/App.tsx`
- `frontend-display/src/App.css`
- `frontend-admin/src/api/client.ts`
- `frontend-admin/src/App.tsx`
- `docs/plans/2026-06-02-long-term-quant-system-upgrade.md`
- `docs/stage-records/phase-5-indicators.md`

## 3. 完成内容

- 指标服务返回统一 `{ timestamp, value }` 时间序列，短窗口不足时保留 `null`。
- MACD 与展示端既有算法保持同口径，`hist = (dif - dea) * 2`。
- RSI 使用 Wilder 平滑，横盘样本输出中性 50。
- BOLL 使用总体标准差，便于样例测试复现。
- 每次网格触发会记录参考价、触发阈值、涨跌幅、MA 过滤规则和最终决策。
- 客户报告优先消费后端指标；缺少后端指标时仍保留前端 fallback。
- 管理端可以在回测列表中扫到最新信号、执行数和拦截数。

## 4. 验证结果

- 目标后端测试：`.venv\Scripts\python.exe -m pytest backend\tests\test_indicators.py backend\tests\test_backtests.py backend\tests\test_snapshots.py`，结果 `20 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `49 passed`。
- 展示端构建：`cd frontend-display; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 管理端构建：`cd frontend-admin; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 客户报告浏览器 smoke：使用本地当前代码后端生成临时 Phase 5 快照；报告页显示信号摘要，payload 顶层和嵌套指标均存在，3 个 canvas 网格采样均非空，桌面和移动端无应用 console error。
- 管理端浏览器 smoke：回测任务表显示“信号”列，复核面板显示“最新信号”“执行/拦截”“信号决策”，无应用 console error。

## 5. 已知说明

- 本阶段不做指标参数优化，也不引入策略自动调参。
- 信号解释当前以规则触发原因和过滤决策为主，还不是自然语言投顾级解释。
- 浏览器 canvas 像素采样触发过浏览器自身 `getImageData` 性能 warning，该 warning 来自验证脚本，不是应用代码。
- 本地存在旧的 8000/8001 后端进程；Phase 5 烟测另开 8002 当前代码后端和 5173 展示端完成，不影响既有服务。

## 6. 停止条件检查

当前未触发停止条件。

## 7. 下一阶段提示

Phase 6 将进入数据库与运维硬化。优先建立迁移基线和数据库启动检查，不应直接重写数据模型。
