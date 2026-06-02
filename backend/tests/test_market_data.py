from fastapi.testclient import TestClient

from app.main import app


def login_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_instrument(client: TestClient, token: str, symbol: str) -> int:
    response = client.post(
        "/api/instruments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "symbol": symbol,
            "exchange": "SH",
            "name": f"{symbol} test stock",
            "asset_type": "stock",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_admin_can_import_and_query_csv_bars() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TCSV01")

        import_response = client.post(
            "/api/market-data/import-csv",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "source": "csv",
                "csv_text": (
                    "timestamp,open,high,low,close,volume\n"
                    "2026-01-02 09:35:00,10,10.5,9.8,10.2,1000\n"
                    "2026-01-02 09:40:00,10.2,10.8,10.1,10.7,1200\n"
                ),
            },
        )

        assert import_response.status_code == 200
        task = import_response.json()
        assert task["status"] == "succeeded"
        assert task["source"] == "csv"
        assert task["instrument_id"] == instrument_id
        assert task["frequency"] == "5m"
        assert task["adjust"] == ""
        assert task["rows_imported"] == 2
        assert task["rows_updated"] == 0
        assert task["request_params"]["source"] == "csv"

        bars_response = client.get(
            f"/api/market-data/bars?instrument_id={instrument_id}&frequency=5m&limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert bars_response.status_code == 200
        bars = bars_response.json()
        assert len(bars) == 2
        assert bars[0]["timestamp"].startswith("2026-01-02T09:35:00")
        assert bars[0]["adjust"] == ""
        assert bars[1]["close"] == 10.7

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "market_data.import_csv.succeeded" in actions


def test_admin_can_check_market_data_completeness() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TCSV11")

        import_response = client.post(
            "/api/market-data/import-csv",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "source": "csv",
                "csv_text": (
                    "timestamp,open,high,low,close,volume\n"
                    "2026-01-02 09:35:00,10,10.5,9.8,10.2,1000\n"
                    "2026-01-02 09:45:00,10.2,10.8,10.1,10.7,1200\n"
                ),
            },
        )
        assert import_response.status_code == 200

        response = client.get(
            f"/api/market-data/completeness?instrument_id={instrument_id}&frequency=5m",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        completeness = response.json()
        assert completeness["status"] == "warning"
        assert completeness["bar_count"] == 2
        assert completeness["expected_bar_count"] == 3
        assert completeness["missing_bar_count"] == 1
        assert completeness["gap_count"] == 1
        assert completeness["largest_gap_minutes"] == 10
        assert completeness["completeness_ratio"] == 0.666667


def test_completeness_reports_empty_data_clearly() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TCSV12")

        response = client.get(
            f"/api/market-data/completeness?instrument_id={instrument_id}&frequency=5m",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        completeness = response.json()
        assert completeness["status"] == "empty"
        assert completeness["bar_count"] == 0
        assert completeness["message"].startswith("No bars found")


def test_reimport_updates_existing_bar_without_duplicates() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TCSV02")

        payload = {
            "instrument_id": instrument_id,
            "frequency": "1d",
            "source": "csv",
            "csv_text": (
                "timestamp,open,high,low,close,volume\n"
                "2026-01-02 00:00:00,10,11,9,10.5,1000\n"
            ),
        }
        first_response = client.post(
            "/api/market-data/import-csv",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert first_response.status_code == 200

        second_response = client.post(
            "/api/market-data/import-csv",
            headers={"Authorization": f"Bearer {token}"},
            json={**payload, "csv_text": "timestamp,open,high,low,close,volume\n2026-01-02 00:00:00,10,12,8,11.5,1500\n"},
        )
        assert second_response.status_code == 200
        assert second_response.json()["rows_updated"] == 1

        bars_response = client.get(
            f"/api/market-data/bars?instrument_id={instrument_id}&frequency=1d&limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        bars = bars_response.json()
        assert len(bars) == 1
        assert bars[0]["adjust"] == ""
        assert bars[0]["close"] == 11.5
        assert bars[0]["volume"] == 1500


def test_invalid_csv_import_fails_without_partial_bars() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TCSV03")

        response = client.post(
            "/api/market-data/import-csv",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "source": "csv",
                "csv_text": (
                    "timestamp,open,high,low,close,volume\n"
                    "2026-01-02 09:35:00,10,10.5,9.8,10.2,1000\n"
                    "bad-time,10.2,10.8,10.1,10.7,1200\n"
                ),
            },
        )

        assert response.status_code == 400
        assert "Invalid timestamp" in response.json()["detail"]

        bars_response = client.get(
            f"/api/market-data/bars?instrument_id={instrument_id}&frequency=5m&limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert bars_response.json() == []


def test_admin_can_fetch_public_bars_with_provider(monkeypatch) -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TPUB01")

        def fake_fetch_public_bars(session, **kwargs):
            from app.services.market_data import ParsedBar, upsert_bars
            from datetime import datetime

            assert kwargs["provider_name"] == "akshare"
            return upsert_bars(
                session,
                instrument_id=kwargs["instrument_id"],
                frequency=kwargs["frequency"],
                adjust=kwargs["adjust"],
                source="akshare",
                data_version="akshare:test",
                parsed_bars=[
                    ParsedBar(
                        timestamp=datetime.fromisoformat("2026-01-02 09:35:00"),
                        open=10,
                        high=10.5,
                        low=9.8,
                        close=10.2,
                        volume=1000,
                    ),
                    ParsedBar(
                        timestamp=datetime.fromisoformat("2026-01-02 09:40:00"),
                        open=10.2,
                        high=10.8,
                        low=10.1,
                        close=10.7,
                        volume=1200,
                    ),
                ],
            )

        monkeypatch.setattr("app.api.market_data.fetch_public_bars", fake_fetch_public_bars)

        fetch_response = client.post(
            "/api/market-data/fetch-public",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "start_date": "2026-01-02 09:30:00",
                "end_date": "2026-01-02 15:00:00",
            },
        )

        assert fetch_response.status_code == 200
        task = fetch_response.json()
        assert task["source"] == "akshare"
        assert task["instrument_id"] == instrument_id
        assert task["frequency"] == "5m"
        assert task["adjust"] == ""
        assert task["status"] == "succeeded"
        assert task["rows_imported"] == 2
        assert task["request_params"]["provider"] == "akshare"

        bars_response = client.get(
            f"/api/market-data/bars?instrument_id={instrument_id}&frequency=5m&limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        bars = bars_response.json()
        assert len(bars) == 2
        assert bars[0]["source"] == "akshare"
        assert bars[0]["adjust"] == ""
        assert bars[0]["data_version"] == "akshare:test"

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "market_data.fetch_public.succeeded" in actions


def test_public_fetch_failure_is_recorded(monkeypatch) -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TPUB02")

        def fake_fetch_public_bars(session, **kwargs):
            raise ValueError("Public data provider returned no bars")

        monkeypatch.setattr("app.api.market_data.fetch_public_bars", fake_fetch_public_bars)

        response = client.post(
            "/api/market-data/fetch-public",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "start_date": "2026-01-02 09:30:00",
                "end_date": "2026-01-02 15:00:00",
            },
        )

        assert response.status_code == 400
        assert "no bars" in response.json()["detail"]

        tasks_response = client.get(
            "/api/market-data/import-tasks",
            headers={"Authorization": f"Bearer {token}"},
        )
        latest_task = tasks_response.json()[0]
        assert latest_task["source"] == "akshare"
        assert latest_task["frequency"] == "5m"
        assert latest_task["status"] == "failed"
        assert "no bars" in latest_task["message"]
