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
        json={"symbol": symbol, "exchange": "SH", "name": f"{symbol} paper stock", "asset_type": "stock"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_parameter_set(client: TestClient, token: str) -> int:
    response = client.post(
        "/api/strategy-parameter-sets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "strategy_id": "rolling_t_grid",
            "name": "Paper config",
            "parameters": {"grid_percent": 1.0, "enable_ma_filter": False},
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def import_bars(client: TestClient, token: str, instrument_id: int) -> None:
    response = client.post(
        "/api/market-data/import-csv",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "instrument_id": instrument_id,
            "frequency": "5m",
            "source": "csv",
            "csv_text": (
                "timestamp,open,high,low,close,volume\n"
                "2026-01-02 09:35:00,10,10.5,9.8,10.0,1000\n"
                "2026-01-02 09:40:00,10.0,10.7,9.9,10.4,1200\n"
                "2026-01-02 09:45:00,10.4,10.9,10.2,10.8,1500\n"
            ),
        },
    )
    assert response.status_code == 200


def test_admin_can_create_paper_run_from_saved_parameter_set() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TPAPER01")
        parameter_set_id = create_parameter_set(client, token)
        import_bars(client, token, instrument_id)

        response = client.post(
            "/api/paper-runs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "parameter_set_id": parameter_set_id,
                "initial_cash": 100000,
            },
        )

        assert response.status_code == 200
        paper_run = response.json()
        assert paper_run["status"] == "succeeded"
        assert paper_run["strategy_id"] == "rolling_t_grid"
        assert paper_run["latest_equity"] == 103607.69
        assert paper_run["config"]["metrics"]["latest_signal"] == "sell"
        assert paper_run["config"]["result_payload"]["paper_summary"]["latest_signal"] == "sell"

        list_response = client.get(
            "/api/paper-runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == paper_run["id"]

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "paper_run.create.succeeded" in actions


def test_paper_run_fails_clearly_when_bars_are_missing() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TPAPER02")
        parameter_set_id = create_parameter_set(client, token)

        response = client.post(
            "/api/paper-runs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "parameter_set_id": parameter_set_id,
            },
        )

        assert response.status_code == 400
        assert "No bars found" in response.json()["detail"]
