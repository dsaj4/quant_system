# Demo Runbook

日期：2026-06-02

用途：记录本地客户 demo 的可复跑步骤，避免因为端口、数据库或密钥配置不一致导致误判。本文档不保存任何真实 token、分享链接 token 或账号密钥。

## 1. 启动前检查

在 `E:\Project\quant` 执行：

```powershell
git branch --show-current
git status --short
```

确认项：

- 当前长期改造分支应为 `codex/long-term-quant-upgrade`。
- `.env` 或 `backend\.env` 可在本地存在，但不能提交。
- Tushare token 只能通过本地环境变量或 `.env` 提供。
- 不要把本地 SQLite、截图、日志、`.venv`、`node_modules` 加入提交。

## 2. 后端启动

从项目根目录启动（推荐）：

```powershell
cd E:\Project\quant
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

或从 `backend` 目录启动：

工作目录：

```powershell
cd E:\Project\quant\backend
```

推荐使用项目虚拟环境：

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001
```

说明：

- 如果 `8001` 被占用，可以换一个空闲端口，但前端 API 地址也要同步调整。
- 如果报告接口返回 404，优先检查是否连接了正确的本地数据库。
- 如果 health 标记 Tushare 未配置，说明本地 token 没有被当前后端进程读取。
- 新环境如需走正式 schema 初始化，可先执行 `.\.venv\Scripts\python.exe -m alembic upgrade head`。

## 3. 管理端启动

```powershell
cd E:\Project\quant\frontend-admin
npm.cmd run dev
```

默认端口：

- `http://127.0.0.1:5183`

管理端用于：

- 创建或选择标的。
- 导入真实或 CSV 行情数据。
- 发起回测。
- 发布报告快照和分享链接。
- 查看数据源、任务和运行状态。

## 4. 展示端启动

```powershell
cd E:\Project\quant\frontend-display
npm.cmd run dev
```

默认端口：

- `http://127.0.0.1:5184`

若需要使用其他端口，例如 `5174`：

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5174
```

展示端 URL 形态：

```text
http://127.0.0.1:<display-port>/?token=<share-token>
```

不要把 `<share-token>` 写入版本库文档。

## 5. 茅台真实数据 demo 路径

目标 demo：

- 标的：贵州茅台
- 代码：`600519`
- 交易所：`SH`
- 数据源：Tushare Pro
- 复权：`qfq`
- 频率：日线 `1d`
- 示例区间：2024-01-01 到 2026-05-29

推荐流程：

1. 后端 health 检查 Tushare 是否 configured。
2. 在管理端创建或选择 `600519.SH`。
3. 使用 Tushare、`1d`、`qfq`、指定日期区间拉取行情。
4. 确认导入任务记录了 provider、frequency、adjust、rows imported、rows updated。
5. 发起回测。
6. 发布 snapshot。
7. 创建 share link。
8. 打开展示端报告 URL。

验收重点：

- 指标区非空。
- K 线或净值图非空。
- 交易记录表可阅读。
- 报告显示数据源、复权、区间、假设和风险披露。
- 浏览器控制台没有新增错误。

## 6. 离线 CSV demo 路径

当 Tushare token、网络或额度不稳定时，可以用固定 CSV 复跑完整流程。示例数据：

```csv
timestamp,open,high,low,close,volume
2026-01-02 09:35:00,10,10.5,9.8,10.0,1000
2026-01-02 09:40:00,10.0,10.7,9.9,10.4,1200
2026-01-02 09:45:00,10.4,10.9,10.2,10.8,1500
2026-01-02 09:50:00,10.8,10.9,10.1,10.2,1300
2026-01-02 09:55:00,10.2,10.6,10.0,10.5,1100
```

推荐流程：

1. 管理端创建一个演示标的，例如 `DEMO001.SH`。
2. 在行情数据模块使用 CSV 导入，frequency 选择 `5m`。
3. 使用 `rolling_t_grid` 参数集运行回测。
4. 发布 snapshot 并打开客户报告。
5. 再运行一次模拟运行，确认管理端 paper run 表显示信号、模拟成交和状态流转。

验收重点：

- 回测报告能显示指标、K 线、交易表、风险披露。
- paper run 成功记录包含 `pending -> running -> succeeded`。
- 故意选择无 K 线标的运行 paper run 时，应生成 failed 记录和失败原因。

## 7. 常见问题

### 报告 404

优先检查：

- 展示端是否指向正确后端 API。
- share token 是否属于当前后端连接的数据库。
- snapshot 或 share link 是否被撤销。
- 后端端口是否与展示端配置一致。

### 数据源未配置

优先检查：

- `.env` 是否存在于正确目录。
- `TUSHARE_TOKEN` 是否被当前后端进程读取。
- 后端是否重启过。

### 数据为空

优先检查：

- symbol 和 exchange 是否能转换为 Tushare `ts_code`，例如 `600519.SH`。
- 日期格式是否为后端 API 接受的格式。
- 频率是否为当前 Tushare adapter 支持范围。
- 复权参数是否为允许的空值、`qfq` 或 `hfq`。

### 前端页面打开但无图表

优先检查：

- public snapshot API 是否返回 `result_payload`。
- payload 是否包含 `candles`、`equity_curve` 或交易数据。
- 浏览器控制台是否有脚本错误。

## 8. 发布前验证命令

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

展示端：

```powershell
cd frontend-display
npm.cmd run build
```

管理端：

```powershell
cd frontend-admin
npm.cmd run build
```

真实数据 smoke：

- 只在自动测试通过后运行。
- 使用最小必要区间。
- 记录目标、日期区间、返回行数。
- 不在日志或文档中写入 token。

## 9. 演示边界

- 客户展示端是只读报告，不允许客户改参数或触发交易。
- paper run 是模拟监控，不是实盘下单。
- 当前默认数据库仍是 SQLite；PostgreSQL/TimescaleDB 是后续生产化路线。
- JQData 暂未购买，BaoStock 第一版仅预留 registry，不宣称已接通。
- 分享链接 token 不写入文档、commit 或截图说明。
