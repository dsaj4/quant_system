from fastapi.testclient import TestClient

from app.main import app


def login_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_can_save_parameter_set_with_defaults() -> None:
    with TestClient(app) as client:
        token = login_token(client)

        response = client.post(
            "/api/strategy-parameter-sets",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "strategy_id": "rolling_t_grid",
                "name": "Default rolling T config",
                "parameters": {"grid_percent": 2.0},
            },
        )

        assert response.status_code == 200
        parameter_set = response.json()
        assert parameter_set["strategy_id"] == "rolling_t_grid"
        assert parameter_set["parameters"]["grid_percent"] == 2.0
        assert parameter_set["parameters"]["base_position_percent"] == 50
        assert parameter_set["parameters"]["enable_ma_filter"] is True

        list_response = client.get(
            "/api/strategy-parameter-sets",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert any(item["name"] == "Default rolling T config" for item in list_response.json())

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "strategy_parameter_set.create" in actions


def test_admin_can_save_a_share_t0_vwap_parameter_set_with_defaults() -> None:
    with TestClient(app) as client:
        token = login_token(client)

        response = client.post(
            "/api/strategy-parameter-sets",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "strategy_id": "a_share_t0_vwap",
                "name": "A-share T0 VWAP config",
                "parameters": {"channel_k": 1.5},
            },
        )

        assert response.status_code == 200
        parameter_set = response.json()
        assert parameter_set["strategy_id"] == "a_share_t0_vwap"
        assert parameter_set["parameters"]["channel_k"] == 1.5
        assert parameter_set["parameters"]["channel_window"] == 20
        assert parameter_set["parameters"]["base_position_percent"] == 40
        assert parameter_set["parameters"]["buy_fee_rate"] == 0.00026
        assert parameter_set["parameters"]["sell_fee_rate"] == 0.00076


def test_strategy_parameter_set_rejects_unknown_strategy() -> None:
    with TestClient(app) as client:
        token = login_token(client)

        response = client.post(
            "/api/strategy-parameter-sets",
            headers={"Authorization": f"Bearer {token}"},
            json={"strategy_id": "missing_strategy", "name": "Bad config", "parameters": {}},
        )

        assert response.status_code == 400
        assert "Unknown strategy" in response.json()["detail"]


def test_strategy_parameter_set_rejects_out_of_range_value() -> None:
    with TestClient(app) as client:
        token = login_token(client)

        response = client.post(
            "/api/strategy-parameter-sets",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "strategy_id": "rolling_t_grid",
                "name": "Bad grid config",
                "parameters": {"grid_percent": 99},
            },
        )

        assert response.status_code == 400
        assert "grid_percent" in response.json()["detail"]
