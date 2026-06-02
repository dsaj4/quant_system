# Phase 0 Baseline Record

日期：2026-06-02

阶段：Phase 0 基线冻结与演示保护

状态：verified

## 1. 执行范围

Phase 0 只做基线冻结、demo runbook、报告 smoke 保护和验证记录。此阶段不重写回测引擎，不改前端视觉目标，不做数据库生产化迁移。

## 2. 当前分支

- 分支：`codex/long-term-quant-upgrade`
- 来源：用户已授权长期无人值守执行，并授权创建分支和按 Phase 阶段提交。

## 3. 当前工作区基线

执行 Phase 0 前，工作区已有多项未提交改动，主要涉及：

- Tushare 真实数据源接入。
- provider registry 和 health 状态。
- Bar 复权唯一键和数据导入任务字段。
- 后端市场数据、调度、schema 测试。
- 客户展示端报告页面调整。
- 外部审计和项目状态文档。
- 长期无人值守改造计划文档。

不应提交的本地文件：

- `.env`、`backend\.env`
- 本地 SQLite 或数据库文件。
- `data/`、`log/`、`.venv/`、`node_modules/`。
- 临时截图，除非后续明确作为文档资产纳入。

## 4. Phase 0 验收门禁

已执行：

- 报告 targeted 测试：`.venv\Scripts\python.exe -m pytest backend\tests\test_snapshots.py backend\tests\test_backtests.py`，结果 `9 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `35 passed`。
- 展示端构建：`cd frontend-display; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 文档与代码密钥扫描：未发现真实 Tushare token 或真实报告 token。
- 浏览器打开现有客户报告，核心指标、图表区域、交易表、假设和风险披露可读。
- 浏览器控制台：`Errors: 0, Warnings: 0`。

## 5. 停止条件检查

当前未触发停止条件。

需要继续关注：

- 当前真实报告 token 不写入版本库。
- 如果本地报告无法访问，需要先判断端口、数据库和后端进程，而不是直接改业务代码。

## 6. 阶段记录

- 2026-06-02：开始 Phase 0，建立 runbook 和基线记录。
- 2026-06-02：补充 snapshot smoke 测试，验证新报告核心字段和旧式最小 payload 公开读取兼容。
- 2026-06-02：完成 Phase 0 验证门禁，准备阶段提交。
