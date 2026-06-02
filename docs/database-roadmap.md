# Database Roadmap

日期：2026-06-02

## 1. 当前结论

当前默认数据库继续使用 SQLite：它适合本地 demo、单机开发、快速复制和低运维成本。系统从 Phase 6 开始引入 Alembic migration baseline，为后续 PostgreSQL 或 TimescaleDB 部署做准备，但不在本阶段切换默认数据库。

## 2. 当前数据库职责

- SQLite：当前默认开发/demo 数据库，路径由 `QUANT_DATABASE_URL` 控制，默认值为 `sqlite:///./data/quant_system.db`。
- Alembic：正式 schema 历史记录和空库建库入口。
- `backend/app/services/schema.py`：SQLite 开发兜底升级，只处理历史开发库的少量补列和 `bar` 唯一键重建。
- `/api/health`：暴露 schema 状态、数据库 dialect、migration 版本状态和开发兜底是否启用。

## 3. Migration 使用

空库初始化：

```powershell
$env:QUANT_DATABASE_URL = "sqlite:///./data/quant_system.db"
.\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:\QUANT_DATABASE_URL
```

生成新迁移：

```powershell
$env:QUANT_DATABASE_URL = "sqlite:///./data/migration_check.db"
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe schema change"
Remove-Item Env:\QUANT_DATABASE_URL
```

回滚说明：

- 本项目允许本地开发库回滚，但真实客户数据回滚前必须先备份。
- 对含业务数据的库执行 `alembic downgrade` 前，需要人工确认影响范围。
- 不允许在未备份的情况下对生产或客户演示库执行破坏性迁移。

## 4. SQLite 保留范围

SQLite 适合：

- 本地 demo。
- 单用户或小规模研究环境。
- 快速生成客户展示快照。
- 自动测试和 CI。

SQLite 不适合：

- 多用户高并发写入。
- 大规模分钟线长期存储。
- 多策略并发调度和高频查询。
- 跨机器部署和严格备份恢复流程。

## 5. PostgreSQL 目标路线

PostgreSQL 是下一阶段生产化优先目标。迁移前需要确认：

- 已有数据是否需要迁移，还是允许从空库开始。
- `QUANT_DATABASE_URL`、备份目录、权限账号和连接池参数。
- 所有 JSON 字段在 PostgreSQL 下是否需要升级为 JSONB。
- 数据量增长后，`bar` 表和查询索引是否满足回测与报告查询。

优先迁移对象：

- `instrument`
- `bar`
- `strategyparameterset`
- `backtestrun`
- `publishedsnapshot`
- `sharelink`
- `operationlog`
- `dataimporttask`
- `marketdataschedule`

## 6. TimescaleDB 候选设计

TimescaleDB 暂不作为强制依赖。未来如分钟线或多标的大规模行情成为主要瓶颈，可以优先考虑：

- 将 `bar` 作为 hypertable，时间列为 `timestamp`。
- 维度字段保留 `instrument_id`、`frequency`、`adjust`。
- 保留唯一约束逻辑：`instrument_id + frequency + timestamp + adjust`。
- 为常用查询保留组合索引：`instrument_id, frequency, adjust, timestamp`。
- 对历史分钟线设置可选压缩和保留策略。

## 7. 备份与恢复

SQLite：

- 停止写入后复制 `data/quant_system.db`。
- 备份文件命名建议包含日期和阶段，例如 `quant_system_2026-06-02_phase6.db`。
- 恢复前先保留当前库副本，再替换目标库。

PostgreSQL：

- 使用 `pg_dump` 做逻辑备份。
- 使用 `pg_restore` 或 `psql` 恢复。
- migration 前后各做一次备份。
- 对外演示环境需要记录当前 migration revision。

## 8. 停止条件

以下情况必须暂停并人工确认：

- 需要把当前 SQLite 真实数据迁移到 PostgreSQL。
- 迁移包含删表、删列、改主键或改唯一键。
- 生产/演示库缺少备份。
- TimescaleDB 扩展权限不可用。
- migration 与当前模型存在无法自动解决的差异。

## 9. 下一步

Phase 6 之后的数据库工作建议顺序：

1. 为新增模型变更继续写 Alembic revision。
2. 在可选 PostgreSQL 环境中跑 `alembic upgrade head`。
3. 加入定期备份脚本和恢复演练记录。
4. 当分钟线数据规模明显增长后，再评估 TimescaleDB。
