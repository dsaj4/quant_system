from dataclasses import dataclass

from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel

from app.models import Bar


@dataclass(frozen=True)
class SchemaReport:
    status: str
    missing_tables: list[str]
    missing_columns: dict[str, list[str]]
    dialect: str
    migration_status: str
    migration_revision: str | None
    development_fallback_enabled: bool


def _migration_state(engine: Engine, existing_tables: set[str]) -> tuple[str, str | None]:
    if "alembic_version" not in existing_tables:
        return "not_versioned", None

    try:
        with engine.connect() as connection:
            revisions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    except Exception:
        return "unreadable", None

    if not revisions:
        return "empty_version_table", None
    return "versioned", str(revisions[-1])


def check_database_schema(engine: Engine) -> SchemaReport:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = {table.name: table for table in SQLModel.metadata.sorted_tables}

    missing_tables = sorted(table_name for table_name in expected_tables if table_name not in existing_tables)
    missing_columns: dict[str, list[str]] = {}

    for table_name, table in expected_tables.items():
        if table_name in missing_tables:
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        expected_columns = {column.name for column in table.columns}
        missing = sorted(expected_columns - existing_columns)
        if missing:
            missing_columns[table_name] = missing

    status = "ok" if not missing_tables and not missing_columns else "mismatch"
    migration_status, migration_revision = _migration_state(engine, existing_tables)
    return SchemaReport(
        status=status,
        missing_tables=missing_tables,
        missing_columns=missing_columns,
        dialect=engine.dialect.name,
        migration_status=migration_status,
        migration_revision=migration_revision,
        development_fallback_enabled=engine.dialect.name == "sqlite",
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _column_definitions_for(table_name: str) -> dict[str, str]:
    return {
        "bar": {
            "adjust": "VARCHAR NOT NULL DEFAULT ''",
        },
        "dataimporttask": {
            "instrument_id": "INTEGER",
            "frequency": "VARCHAR NOT NULL DEFAULT ''",
            "adjust": "VARCHAR NOT NULL DEFAULT ''",
            "rows_imported": "INTEGER NOT NULL DEFAULT 0",
            "rows_updated": "INTEGER NOT NULL DEFAULT 0",
            "request_params": "JSON NOT NULL DEFAULT '{}'",
        },
        "marketdataschedule": {
            "provider": "VARCHAR NOT NULL DEFAULT 'tushare'",
        },
    }.get(table_name, {})


def _add_missing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name in SQLModel.metadata.tables:
            if table_name not in existing_tables:
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_definition in _column_definitions_for(table_name).items():
                if column_name in existing_columns:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE {_quote_identifier(table_name)} "
                        f"ADD COLUMN {_quote_identifier(column_name)} {column_definition}"
                    )
                )


def _bar_identity_constraint_includes_adjust(engine: Engine) -> bool:
    inspector = inspect(engine)
    if "bar" not in inspector.get_table_names():
        return True

    for constraint in inspector.get_unique_constraints("bar"):
        if constraint.get("name") != "uq_bar_identity":
            continue
        return "adjust" in constraint.get("column_names", [])

    for index in inspector.get_indexes("bar"):
        if not index.get("unique"):
            continue
        columns = set(index.get("column_names", []))
        if {"instrument_id", "frequency", "timestamp"}.issubset(columns):
            return "adjust" in columns

    return False


def _rebuild_bar_table_with_adjust_identity(engine: Engine) -> None:
    if engine.dialect.name != "sqlite" or _bar_identity_constraint_includes_adjust(engine):
        return

    inspector = inspect(engine)
    old_columns = {column["name"] for column in inspector.get_columns("bar")}
    copy_columns = [
        "id",
        "instrument_id",
        "frequency",
        "timestamp",
        "adjust",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "data_version",
    ]

    select_columns = []
    for column_name in copy_columns:
        if column_name in old_columns:
            select_columns.append(_quote_identifier(column_name))
        elif column_name == "adjust":
            select_columns.append("'' AS adjust")
        else:
            raise RuntimeError(f"Cannot rebuild bar table; missing required column: {column_name}")

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE bar RENAME TO bar_legacy_identity"))
        legacy_indexes = connection.execute(text("PRAGMA index_list('bar_legacy_identity')")).mappings().all()
        for legacy_index in legacy_indexes:
            index_name = str(legacy_index["name"])
            if index_name.startswith("sqlite_autoindex"):
                continue
            connection.execute(text(f"DROP INDEX {_quote_identifier(index_name)}"))
        Bar.__table__.create(connection)
        connection.execute(
            text(
                f"INSERT INTO bar ({', '.join(_quote_identifier(column) for column in copy_columns)}) "
                f"SELECT {', '.join(select_columns)} FROM bar_legacy_identity"
            )
        )
        connection.execute(text("DROP TABLE bar_legacy_identity"))


def upgrade_database_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    _add_missing_columns(engine)
    _rebuild_bar_table_with_adjust_identity(engine)
