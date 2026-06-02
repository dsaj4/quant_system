# Phase 2 Backtest Engine Record

日期：2026-06-02

阶段：Phase 2 回测引擎真实化

状态：verified

## 1. 执行范围

本阶段把回测引擎从价格比例演示升级为资金/仓位驱动的模拟执行：

- 应用 `initial_cash`。
- 应用 `base_position_percent` 初始基础仓位。
- 应用 `trade_position_percent` 单次交易仓位。
- 支持 `fee_rate` 手续费率。
- 支持 `slippage_bps` 单边滑点。
- 生成交易后现金、持仓、费用、滑点、权益和仓位字段。

## 2. 完成内容

- `run_single_instrument_backtest` 改为现金 + 持仓数量 + 当前权益的状态机。
- 初始按基础仓位建仓，后续按网格阈值买入/卖出目标权益比例。
- 增加 MA filter 执行入口：启用时用当前 close 与移动均线约束买卖方向。
- `trade_table` 增加 `execution_price`、`quantity`、`amount`、`fee`、`slippage`、`cash_after`、`equity_after`、`position_after`。
- `result_payload` 增加 `orders` 和 `execution_assumptions`。
- 基准曲线改为首根 K 线买入持有估算，不再复用策略权益曲线。
- 策略参数 registry 增加 `fee_rate` 和 `slippage_bps`。
- snapshot 假设读取 `execution_assumptions`，报告可显示手续费和滑点是否计入。
- paper run 测试口径同步到新回测引擎。

## 3. 验证结果

- Phase 2 targeted tests：`.venv\Scripts\python.exe -m pytest backend\tests\test_backtests.py backend\tests\test_snapshots.py backend\tests\test_strategy_parameter_sets.py`，结果 `16 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `39 passed`。
- 展示端构建：`cd frontend-display; npm.cmd run build`，结果通过，保留 Vite chunk size warning。
- 管理端构建：`cd frontend-admin; npm.cmd run build`，结果通过，保留 Vite chunk size warning。

## 4. 语义变化

旧引擎把累计收益近似看成标的价格涨跌幅。新引擎按基础仓位和单次交易仓位计算，因此同一价格序列下累计收益会低于满仓买入持有。

示例：

- 单标的 API 测试样例累计收益从旧口径 `0.02` 调整为新口径约 `0.017718`。
- 组合 API 测试样例累计收益从旧口径 `0.02` 调整为新口径约 `0.009005`。
- paper run 样例 latest equity 从旧口径 `108000` 调整为新口径 `103607.69`。

## 5. 停止条件检查

当前未触发停止条件。

## 6. 下一阶段提示

Phase 3 需要把管理端真实数据工作流补齐。由于策略 registry 已新增 `fee_rate` 和 `slippage_bps`，管理端策略参数表单已经能通过 registry 自动看到参数，但 Phase 3 仍需要重点处理 provider、adjust、frequency、导入任务状态和 Tushare 默认源。
