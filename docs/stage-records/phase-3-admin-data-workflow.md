# Phase 3 Admin Data Workflow Record

日期：2026-06-02

阶段：Phase 3 管理端数据工作流

状态：verified

## 1. 执行范围

本阶段把真实数据导入工作流从“后端 API 已支持”推进到“管理端可操作、可观察”：

- 公共行情拉取默认 Tushare。
- AkShare 仍可显式选择作为免费兜底。
- JQData 和 BaoStock 只显示为预留，不误导为已可用。
- 管理端公共拉取表单支持 provider、frequency、adjust。
- 数据导入任务表展示 provider/source、周期、复权、行数和请求参数。
- 行情计划支持 provider。

## 2. 完成内容

- 后端 `PublicFetchRequest` 默认 provider 从 `akshare` 改为 `tushare`。
- 后端 `MarketDataScheduleCreate` 默认 provider 从 `akshare` 改为 `tushare`。
- `MarketDataSchedule` 模型和 SQLite schema fallback 默认 provider 改为 `tushare`。
- 后端测试保留显式 AkShare 拉取路径，并验证默认失败任务记录 Tushare。
- 管理端 API 类型补齐 `DataImportTask.instrument_id/frequency/adjust/request_params`。
- 管理端 API 类型补齐 `Bar.adjust`、`PublicFetchInput.provider`、`MarketDataSchedule.provider`。
- 管理端 bars/completeness 查询支持按 adjust 查询。
- 管理端公共拉取表单默认 `tushare + 1d + qfq`。
- 管理端行情计划表单默认 `tushare + 1d + qfq`。
- 管理端数据导入任务表新增标的、周期、复权、请求参数列。

## 3. 验证结果

- 后端 targeted tests：`.venv\Scripts\python.exe -m pytest backend\tests\test_market_data.py backend\tests\test_market_data_schedules.py backend\tests\test_schema_health.py`，结果 `11 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `39 passed`。
- 管理端构建：`cd frontend-admin; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 浏览器管理端 smoke：`http://127.0.0.1:5183` 可打开并登录。
- 浏览器 DOM 检查：`行情数据管理`、`Tushare Pro`、`前复权 qfq`、`数据导入任务`、`请求参数` 均存在。

## 4. 已知说明

- 浏览器 console 中存在登录前接口自动请求导致的 401 Unauthorized 记录；这属于未登录状态的历史记录，不是本阶段新错误。
- 本阶段没有调用真实 Tushare，仍遵守“自动测试通过后再做最小真实数据测试”的原则。

## 5. 停止条件检查

当前未触发停止条件。

## 6. 下一阶段提示

Phase 4 将进入数据质量与交易日历。当前已有基础 completeness 检查，但还没有基于 Tushare 交易日历的日线预期交易日校验。
