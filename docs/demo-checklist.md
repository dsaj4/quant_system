# Demo Checklist

日期：2026-06-02

用途：客户演示前后逐项确认，避免把本地偶发状态误当成系统问题。

## 1. 启动前

- [ ] 当前分支是 `codex/long-term-quant-upgrade`。
- [ ] `git status --short` 中没有准备误提交的密钥、数据库、截图或日志。
- [ ] `.env` 或 `backend/.env` 只存在本地，不提交。
- [ ] Tushare token 只通过环境变量或本地 `.env` 读取。
- [ ] 如使用新空库，已执行 `.\.venv\Scripts\python.exe -m alembic upgrade head`。
- [ ] `/api/health` 返回 `database=ok`、`schema.status=ok`。

## 2. 服务

- [ ] 后端已启动，端口和前端 API 地址一致。
- [ ] 管理端已启动并可登录。
- [ ] 展示端已启动，能读取当前后端 public snapshot API。
- [ ] 浏览器 console 没有新增应用错误。

## 3. 数据

- [ ] 真实数据 demo 优先使用 `600519.SH`、Tushare、`1d`、`qfq`。
- [ ] 若真实数据不可用，改用 `docs/demo-runbook.md` 中固定 CSV 样例。
- [ ] 导入任务显示 provider、frequency、adjust、rows imported/updated。
- [ ] 数据质量 warning 能被解释，不静默忽略。

## 4. 回测与报告

- [ ] 已选择或创建 `rolling_t_grid` 参数集。
- [ ] 回测成功生成 metrics、equity curve、drawdown curve、position curve、trade table。
- [ ] 客户报告已发布 snapshot。
- [ ] 客户报告链接只口头或临时发送，不写入版本库文档。
- [ ] 客户报告可见核心指标、K 线证据图、交易表、方法假设、风险披露。
- [ ] 报告图表非空，桌面和移动端无明显重叠。

## 5. 模拟运行

- [ ] 成功 paper run 显示 latest signal、decision、position、simulated trades。
- [ ] 展开 paper run 可见状态流转和信号说明。
- [ ] 故意无数据运行时生成 failed paper run，并显示失败原因。
- [ ] 明确说明 paper run 是模拟，不是实盘交易。

## 6. 最终验证命令

- [ ] 后端：`.\.venv\Scripts\python.exe -m pytest backend\tests`
- [ ] 展示端：`cd frontend-display; npm.cmd run build`
- [ ] 管理端：`cd frontend-admin; npm.cmd run build`
- [ ] 可选：真实 Tushare smoke 只在自动测试通过后做最小量调用。

## 7. 客户边界口径

- [ ] 不承诺收益。
- [ ] 不宣称实盘交易已接入。
- [ ] 不宣称 JQData 已购买或 BaoStock 已实现。
- [ ] 不承诺生产 SLA。
- [ ] 数据库生产化路线说明为 PostgreSQL/TimescaleDB 后续阶段，不是当前默认。
