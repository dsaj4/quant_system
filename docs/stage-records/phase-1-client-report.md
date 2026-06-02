# Phase 1 Client Report Record

日期：2026-06-02

阶段：Phase 1 客户报告成熟化

状态：verified

## 1. 执行范围

本阶段目标是让客户报告更完整、更可信、更容易讲清楚。重点包括：

- 后端 report snapshot payload 增加 `report_summary`、`data_summary`、`risk_metrics`、`trade_summary`。
- 后端补充年化收益、年化波动率、Sharpe、Calmar、收益回撤比、平均盈亏等指标。
- 展示端读取新字段，同时兼容旧 snapshot。
- 长交易表不能撑破页面。

## 2. 不做范围

- 不改变回测交易逻辑。
- 不接入新数据源。
- 不做数据库破坏性迁移。

## 3. 计划验证

已执行：

- 报告 payload targeted tests：`.venv\Scripts\python.exe -m pytest backend\tests\test_backtests.py backend\tests\test_snapshots.py`，结果 `11 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `37 passed`。
- `frontend-display` 构建：`npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 浏览器桌面报告 smoke：报告解读、夏普比率、交易摘要、固定高度交易表均可见。
- 浏览器移动宽度 smoke：390px 宽度下摘要区和核心指标可读。
- 浏览器控制台：`Errors: 0, Warnings: 0`。
- 交易表滚动验证：`.table-wrap` 可视高度约 429px，内容高度约 7999px，`tableIsScrollable: true`。

## 4. 完成内容

- 后端新增 `calculate_performance_metrics`，计算年化收益、年化波动率、Sharpe、Calmar、收益回撤比、平均盈利、平均亏损和盈亏比。
- 后端 snapshot payload 新增 `report_summary`、`data_summary`、`risk_metrics`、`trade_summary`。
- snapshot 测试覆盖新 payload 合同和旧式最小 payload 公开读取兼容。
- 展示端新增报告解读区、风险/交易摘要字段和旧 payload 归一化。
- 展示端交易表改为固定高度滚动，避免长交易记录撑破页面。

## 5. 停止条件检查

当前未触发停止条件。

说明：

- 当前浏览器中的茅台报告是旧 snapshot，因此新增后端字段未在该历史 payload 中出现，展示端使用 fallback 文案和 `-` 占位；新发布 snapshot 会带完整新增字段。

## 6. 阶段记录

- 2026-06-02：开始 Phase 1。
- 2026-06-02：完成 Phase 1 后端指标、snapshot payload、展示端摘要和交易表滚动改造。
