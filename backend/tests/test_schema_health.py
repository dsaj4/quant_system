from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlmodel import create_engine

from app.main import app
from app.services.schema import check_database_schema, upgrade_database_schema


def test_health_reports_database_schema_status() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

        assert response.status_code == 200
        payload = response.json()
        assert payload["database"] == "ok"
        assert payload["dependencies"]["database"] == "ok"
        assert payload["dependencies"]["schema"] == "ok"
        assert payload["dependencies"]["scheduler"] == "running"
        assert payload["dependencies"]["public_data_providers"] == "ok"
        assert payload["dependencies"]["primary_data_provider"] in {"configured", "not_configured"}
        assert payload["scheduler"]["status"] == "running"
        assert payload["public_data"]["providers"] == ["tushare", "jqdata", "akshare", "baostock"]
        assert "akshare" in payload["public_data"]["adapter_providers"]
        assert "tushare" in payload["public_data"]["adapter_providers"]
        assert "tushare" in payload["public_data"]["calendar_providers"]
        assert payload["public_data"]["default_provider"] == "tushare"
        assert payload["public_data"]["primary_provider"]["name"] == "tushare"
        assert isinstance(payload["public_data"]["primary_provider"]["is_configured"], bool)
        assert payload["public_data"]["primary_provider"]["adapter_available"] is True
        assert isinstance(payload["public_data"]["configured"]["tushare"], bool)
        assert payload["public_data"]["configured"]["jqdata"] is False
        assert payload["public_data"]["configured"]["akshare"] is True
        provider_details = {item["name"]: item for item in payload["public_data"]["details"]}
        assert provider_details["tushare"]["role"] == "primary"
        assert provider_details["jqdata"]["is_enabled"] is False
        assert provider_details["akshare"]["adapter_available"] is True
        assert payload["schema"]["status"] == "ok"
        assert payload["schema"]["dialect"] == "sqlite"
        assert payload["schema"]["migration_status"] in {"not_versioned", "versioned"}
        assert payload["schema"]["development_fallback_enabled"] is True
        assert payload["schema"]["missing_tables"] == []
        assert payload["schema"]["missing_columns"] == {}


def test_schema_check_finds_missing_columns() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE instrument (id INTEGER PRIMARY KEY)"))

    report = check_database_schema(engine)

    assert report.status == "mismatch"
    assert "instrument" in report.missing_columns
    assert "symbol" in report.missing_columns["instrument"]


def test_schema_upgrade_adds_data_source_columns_and_adjust_identity() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE bar (
                    id INTEGER PRIMARY KEY,
                    instrument_id INTEGER NOT NULL,
                    frequency VARCHAR NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open FLOAT NOT NULL,
                    high FLOAT NOT NULL,
                    low FLOAT NOT NULL,
                    close FLOAT NOT NULL,
                    volume FLOAT NOT NULL DEFAULT 0,
                    source VARCHAR NOT NULL DEFAULT 'manual',
                    data_version VARCHAR NOT NULL DEFAULT '',
                    CONSTRAINT uq_bar_identity UNIQUE (instrument_id, frequency, timestamp)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE dataimporttask (
                    id INTEGER PRIMARY KEY,
                    source VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    message VARCHAR NOT NULL DEFAULT '',
                    started_at DATETIME,
                    finished_at DATETIME,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE marketdataschedule (
                    id INTEGER PRIMARY KEY,
                    instrument_id INTEGER NOT NULL,
                    frequency VARCHAR NOT NULL DEFAULT '5m',
                    start_date VARCHAR NOT NULL,
                    end_date VARCHAR NOT NULL,
                    adjust VARCHAR NOT NULL DEFAULT '',
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    last_run_at DATETIME,
                    last_status VARCHAR,
                    last_message VARCHAR NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE paperrun (
                    id INTEGER PRIMARY KEY,
                    strategy_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    config JSON,
                    latest_equity FLOAT NOT NULL DEFAULT 0,
                    message VARCHAR NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    upgrade_database_schema(engine)

    inspector = inspect(engine)
    bar_columns = {column["name"] for column in inspector.get_columns("bar")}
    task_columns = {column["name"] for column in inspector.get_columns("dataimporttask")}
    schedule_columns = {column["name"] for column in inspector.get_columns("marketdataschedule")}
    paper_run_columns = {column["name"] for column in inspector.get_columns("paperrun")}

    assert "adjust" in bar_columns
    assert {"instrument_id", "frequency", "adjust", "rows_imported", "rows_updated", "request_params"}.issubset(
        task_columns
    )
    assert "provider" in schedule_columns
    assert {"started_at", "finished_at"}.issubset(paper_run_columns)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO bar (
                    instrument_id, frequency, timestamp, adjust, open, high, low, close, volume, source, data_version
                )
                VALUES (1, '5m', '2026-01-02 09:35:00', 'qfq', 10, 11, 9, 10.5, 1000, 'tushare', 'v1')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO bar (
                    instrument_id, frequency, timestamp, adjust, open, high, low, close, volume, source, data_version
                )
                VALUES (1, '5m', '2026-01-02 09:35:00', 'hfq', 10, 12, 8, 11.5, 1200, 'tushare', 'v1')
                """
            )
        )
