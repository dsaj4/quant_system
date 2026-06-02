# Phase 6 数据库与运维硬化记录

日期：2026-06-02

阶段：Phase 6 数据库与运维硬化
状态：verified

## 1. 执行范围

本阶段建立数据库治理基线，不切换默认数据库：

- 新增 Alembic 配置和 baseline migration。
- 保留 SQLite 作为当前 demo 默认数据库。
- 将自动建表和补 schema 限定为 SQLite 开发兜底。
- `/api/health` 增加数据库 dialect、migration 状态和开发兜底状态。
- 新增空库 migration 测试，验证新环境可通过 migration 建库。
- 新增 PostgreSQL/TimescaleDB 路线、备份恢复和停止条件文档。

## 2. 修改文件

- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/20260602_000001_baseline_schema.py`
- `backend/app/api/health.py`
- `backend/app/core/database.py`
- `backend/app/services/schema.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_schema_health.py`
- `requirements.txt`
- `docs/database-roadmap.md`
- `docs/plans/2026-06-02-long-term-quant-system-upgrade.md`
- `docs/stage-records/phase-6-database-operations.md`

## 3. 完成内容

- `alembic upgrade head` 可以对空 SQLite 数据库创建当前完整 schema。
- Alembic env 从 `QUANT_DATABASE_URL` 读取目标库，便于本地、CI 和未来部署复用。
- `SchemaReport` 增加 `dialect`、`migration_status`、`migration_revision`、`development_fallback_enabled`。
- SQLite 仍会在 app 启动时执行 `SQLModel.metadata.create_all` 和开发兜底升级，保持 demo 可用。
- 非 SQLite 数据库不再走自动补 schema 逻辑，后续应先执行 migration。
- 数据库路线文档明确 SQLite 当前边界、PostgreSQL 迁移前置条件、TimescaleDB hypertable 候选和备份恢复要求。

## 4. 验证结果

- 迁移与 schema 目标测试：`.venv\Scripts\python.exe -m pytest backend\tests\test_migrations.py backend\tests\test_schema_health.py`，结果 `4 passed`。
- 后端完整测试：`.venv\Scripts\python.exe -m pytest backend\tests`，结果 `50 passed`。
- Alembic 配置 warning 已通过 `path_separator = os` 清理。

## 5. 已知说明

- 本阶段没有把现有 SQLite 数据迁移到 PostgreSQL，也没有要求部署 TimescaleDB。
- 当前业务库如果尚未执行 Alembic，`/api/health` 会显示 `migration_status = not_versioned`，但 schema 完整时整体仍可用。
- 真实客户数据迁移前必须先备份并人工确认迁移范围。

## 6. 停止条件检查

当前未触发停止条件：

- 未执行不可逆数据迁移。
- 未切换默认数据库。
- 未要求 PostgreSQL/TimescaleDB 权限。

## 7. 下一阶段提示

Phase 7 将进入模拟交易与监控成熟化。应优先让 paper run 的状态、信号、模拟成交和失败原因可追踪。
