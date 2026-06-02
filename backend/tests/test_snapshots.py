from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.snapshots import hash_share_token
from app.core.database import engine
from app.main import app
from app.models import BacktestRun, PublishedSnapshot, ShareLink, SnapshotStatus, TaskStatus, utc_now


def login_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_backtest(client: TestClient, token: str) -> int:
    instrument_response = client.post(
        "/api/instruments",
        headers={"Authorization": f"Bearer {token}"},
        json={"symbol": "TSNAP01", "exchange": "SH", "name": "Snapshot Test", "asset_type": "stock"},
    )
    assert instrument_response.status_code == 200
    instrument_id = instrument_response.json()["id"]

    parameter_response = client.post(
        "/api/strategy-parameter-sets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "strategy_id": "rolling_t_grid",
            "name": "Snapshot config",
            "parameters": {"grid_percent": 1.0, "enable_ma_filter": False},
        },
    )
    assert parameter_response.status_code == 200
    parameter_set_id = parameter_response.json()["id"]

    import_response = client.post(
        "/api/market-data/import-csv",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "instrument_id": instrument_id,
            "frequency": "5m",
            "source": "csv",
            "csv_text": (
                "timestamp,open,high,low,close,volume\n"
                "2026-01-02 09:35:00,10,10.5,9.8,10.0,1000\n"
                "2026-01-02 09:40:00,10.0,10.8,9.9,10.7,1200\n"
            ),
        },
    )
    assert import_response.status_code == 200

    backtest_response = client.post(
        "/api/backtests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "instrument_id": instrument_id,
            "frequency": "5m",
            "parameter_set_id": parameter_set_id,
            "initial_cash": 100000,
        },
    )
    assert backtest_response.status_code == 200
    return backtest_response.json()["id"]


def test_admin_can_publish_snapshot_and_client_can_read_with_token() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token)

        publish_response = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "Published rolling T report"},
        )

        assert publish_response.status_code == 200
        published = publish_response.json()
        assert published["snapshot"]["status"] == "published"
        assert published["snapshot"]["version"] == 1
        assert published["share_token"]
        assert published["snapshot"]["immutable_payload"]["title"] == "Published rolling T report"
        assert published["snapshot"]["immutable_payload"]["metrics"]["bar_count"] == 2
        payload = published["snapshot"]["immutable_payload"]
        assert {
            "title",
            "strategy_id",
            "backtest_config",
            "report_metadata",
            "report_summary",
            "data_summary",
            "risk_metrics",
            "trade_summary",
            "assumptions",
            "data_quality",
            "metrics",
            "result_payload",
            "risk_disclosure",
        }.issubset(payload)
        assert payload["report_summary"]["performance_summary"]
        assert payload["report_summary"]["risk_summary"]
        assert payload["report_summary"]["method_summary"]
        assert payload["data_summary"]["frequency"] == "5m"
        assert payload["risk_metrics"]["max_drawdown"] == payload["metrics"]["max_drawdown"]
        assert payload["trade_summary"]["trade_count"] == payload["metrics"]["trade_count"]
        metadata = published["snapshot"]["immutable_payload"]["report_metadata"]
        assert metadata["scope_label"] == "单支股票"
        assert metadata["target_label"] == "TSNAP01"
        assert metadata["backtest_period"]["start"].startswith("2026-01-02T09:35:00")
        assert metadata["warnings"]
        assumptions = published["snapshot"]["immutable_payload"]["assumptions"]
        assert assumptions["fees_included"] is False
        assert assumptions["slippage_included"] is False
        assert published["snapshot"]["immutable_payload"]["data_quality"]["status"] == "warning"
        assert published["snapshot"]["immutable_payload"]["data_quality"]["warnings"]

        public_response = client.get(f"/api/public/snapshots/{published['share_token']}")
        assert public_response.status_code == 200
        public_snapshot = public_response.json()
        assert public_snapshot["title"] == "Published rolling T report"
        assert public_snapshot["payload"]["metrics"]["cumulative_return"] == 0.035

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "snapshot.publish" in actions


def test_revoked_snapshot_share_token_cannot_be_read() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token)
        publish_response = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "Report to revoke"},
        )
        assert publish_response.status_code == 200
        share_token = publish_response.json()["share_token"]
        snapshot_id = publish_response.json()["snapshot"]["id"]

        revoke_response = client.post(
            f"/api/snapshots/{snapshot_id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert revoke_response.status_code == 200
        assert revoke_response.json()["status"] == "revoked"
        public_response = client.get(f"/api/public/snapshots/{share_token}")
        assert public_response.status_code == 404


def test_admin_can_manage_snapshot_share_links_without_persisting_plain_token() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token)
        publish_response = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "Managed link report"},
        )
        assert publish_response.status_code == 200
        snapshot_id = publish_response.json()["snapshot"]["id"]

        list_response = client.get(
            "/api/share-links",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        links = list_response.json()
        first_link = next(item for item in links if item["snapshot_id"] == snapshot_id)
        assert first_link["snapshot_title"] == "Managed link report"
        assert first_link["is_active"] is True
        assert "share_token" not in first_link

        create_response = client.post(
            f"/api/snapshots/{snapshot_id}/share-links",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["share_token"]
        assert created["share_link"]["snapshot_id"] == snapshot_id

        public_response = client.get(f"/api/public/snapshots/{created['share_token']}")
        assert public_response.status_code == 200

        revoke_response = client.post(
            f"/api/share-links/{created['share_link']['id']}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revoke_response.status_code == 200
        assert revoke_response.json()["is_active"] is False

        revoked_public_response = client.get(f"/api/public/snapshots/{created['share_token']}")
        assert revoked_public_response.status_code == 404

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "share_link.create" in actions
        assert "share_link.revoke" in actions


def test_public_snapshot_can_read_legacy_minimal_payload() -> None:
    with TestClient(app) as client:
        share_token = "legacy-smoke-token"
        with Session(engine) as session:
            backtest = BacktestRun(
                strategy_id="legacy_strategy",
                status=TaskStatus.succeeded,
                config={},
                metrics={},
                result_payload={},
                message="Legacy backtest row for public snapshot compatibility.",
            )
            session.add(backtest)
            session.commit()
            session.refresh(backtest)

            snapshot = PublishedSnapshot(
                backtest_run_id=backtest.id or 0,
                version=1,
                status=SnapshotStatus.published,
                title="Legacy payload",
                immutable_payload={"title": "Legacy payload", "metrics": {"bar_count": 0}},
                published_at=utc_now(),
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)

            session.add(
                ShareLink(
                    snapshot_id=snapshot.id or 0,
                    token_hash=hash_share_token(share_token),
                    is_active=True,
                )
            )
            session.commit()

        public_response = client.get(f"/api/public/snapshots/{share_token}")

        assert public_response.status_code == 200
        payload = public_response.json()
        assert payload["title"] == "Legacy payload"
        assert payload["payload"]["metrics"]["bar_count"] == 0


def test_cannot_publish_failed_or_missing_backtest() -> None:
    with TestClient(app) as client:
        token = login_token(client)

        response = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": 999999, "title": "Missing report"},
        )

        assert response.status_code == 400
        assert "Unknown backtest" in response.json()["detail"]
