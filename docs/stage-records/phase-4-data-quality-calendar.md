# Phase 4 Data Quality Calendar Record

日期：2026-06-02

阶段：Phase 4 数据质量与交易日历

状态：verified

## 1. 执行范围

本阶段补强数据质量解释能力：

- 数据完整性结果支持 warnings。
- 日线完整性支持传入交易日历后识别缺失交易日。
- Tushare trade calendar adapter 预留为 provider calendar。
- 回测结果携带 data quality payload。
- snapshot 报告继承 data quality warning。
- 管理端和展示端能显示新增 warning 字段。

## 2. 完成内容

- `DataCompleteness` 增加 `calendar_source`、`expected_trading_days`、`missing_trading_days`、`warnings`。
- `assess_bar_completeness` 支持 `expected_trading_dates`，可按交易日历计算日线缺失。
- 样本少于 30 根 K 线时，数据质量状态升级为 `warning`。
- 新增 Tushare 交易日历 provider registry 和 `fetch_trading_calendar`。
- `/api/health` 暴露 `calendar_providers`。
- `/api/market-data/completeness` 支持显式 `calendar_provider` 参数；默认不打外网。
- backtest result payload 增加 JSON-safe `data_quality`。
- snapshot metadata 和 data_quality summary 继承回测 data quality warnings。
- 管理端类型和完整性面板展示交易日、缺失交易日和 warnings。
- 展示端风险披露区展示 data quality warnings 和缺失交易日。

## 3. 验证结果

- Phase 4 targeted tests：`.venv\Scripts\python.exe -m pytest backend\tests\test_market_data_contracts.py backend\tests\test_market_data.py backend\tests\test_backtests.py backend\tests\test_snapshots.py backend\tests\test_schema_health.py`，结果 `30 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `42 passed`。
- 管理端构建：`cd frontend-admin; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 展示端构建：`cd frontend-display; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 浏览器管理端 smoke：页面文本包含 `交易日` 和 `缺失交易日`。

## 4. 已知说明

- 真实 Tushare 日历不会在默认完整性检查中自动调用；只有显式传 `calendar_provider=tushare` 时才调用，避免常规管理端操作消耗额度或因 token 缺失失败。
- 分钟线仍沿用间隔缺口估算；交易日历精确校验优先覆盖日线。

## 5. 停止条件检查

当前未触发停止条件。

## 6. 下一阶段提示

Phase 5 将进入指标层和策略解释。当前展示端仍会在缺少后端指标时计算 MA/MACD fallback，下一阶段应把指标计算迁移到后端并写入 snapshot。
