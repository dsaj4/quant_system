from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.services.schema import check_database_schema


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_baseline_upgrades_empty_sqlite_database(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "migration-empty.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("QUANT_DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(config, "head")

        engine = create_engine(database_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        report = check_database_schema(engine)

        assert "alembic_version" in tables
        assert "bar" in tables
        assert "backtestrun" in tables
        assert "narrativerun" in tables
        paper_run_columns = {column["name"] for column in inspector.get_columns("paperrun")}
        assert {"started_at", "finished_at"}.issubset(paper_run_columns)
        narrative_columns = {column["name"] for column in inspector.get_columns("narrativerun")}
        assert {"backtest_run_id", "status", "ai_draft_payload", "reviewed_payload"}.issubset(narrative_columns)
        assert report.status == "ok"
        assert report.migration_status == "versioned"
        assert report.migration_revision == "20260603_000003"
    finally:
        get_settings.cache_clear()
