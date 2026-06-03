from fastapi.testclient import TestClient

from app.main import app
from app.services.narrative_provider import MockNarrativeProvider, ProviderRunStatus


def login_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_backtest(client: TestClient, token: str, symbol: str = "TNARR01") -> int:
    instrument_response = client.post(
        "/api/instruments",
        headers={"Authorization": f"Bearer {token}"},
        json={"symbol": symbol, "exchange": "SH", "name": f"{symbol} narrative stock", "asset_type": "stock"},
    )
    assert instrument_response.status_code == 200
    instrument_id = instrument_response.json()["id"]

    parameter_response = client.post(
        "/api/strategy-parameter-sets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "strategy_id": "rolling_t_grid",
            "name": f"{symbol} narrative config",
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
                "2026-01-02 09:35:00,10,10,10,10.0,1000\n"
                "2026-01-02 09:40:00,10,10.5,10,10.4,1000\n"
                "2026-01-02 09:45:00,10.4,10.8,10.4,10.8,1000\n"
                "2026-01-02 09:50:00,10.8,11.2,10.8,11.2,1000\n"
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


def test_narrative_api_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/narratives/config")

    assert response.status_code in {401, 403}


def test_narrative_config_does_not_leak_secrets() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        response = client.get("/api/narratives/config", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert "api_key" not in str(payload).lower()
    assert "secret" not in str(payload).lower()
    assert set(payload) == {"enabled", "configured", "provider", "llm_provider", "model", "selected_analysts"}
    assert isinstance(payload["selected_analysts"], list)


def test_generate_and_fetch_current_narrative(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.narratives.build_provider",
        lambda: MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Hold"),
    )

    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token, "TNARR02")
        response = client.post(
            "/api/narratives/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "analysis_date": "2026-01-03"},
        )
        assert response.status_code == 200
        generated = response.json()
        assert generated["backtest_run_id"] == backtest_id

        current_response = client.get(
            f"/api/narratives/backtests/{backtest_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert current_response.status_code == 200
    current = current_response.json()
    assert current["status"] == "succeeded"
    assert current["ai_draft_payload"]["label"] == "AI 投研参考结论"
    assert current["provider_raw_suggestion"] == "Hold"


def test_draft_update_approve_and_withdraw_review(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.narratives.build_provider",
        lambda: MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Hold"),
    )

    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token, "TNARR03")
        generated = client.post(
            "/api/narratives/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "analysis_date": "2026-01-03"},
        ).json()
        narrative_id = generated["id"]
        current = client.get(
            f"/api/narratives/backtests/{backtest_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        draft = current["ai_draft_payload"]
        draft["modules"][0]["summary"] = "已人工调整的一句话结论。"

        update_response = client.patch(
            f"/api/narratives/{narrative_id}/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"payload": draft},
        )
        approve_response = client.post(
            f"/api/narratives/{narrative_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"review_note": "ok"},
        )
        withdraw_response = client.post(
            f"/api/narratives/{narrative_id}/withdraw-review",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert update_response.status_code == 200
    assert update_response.json()["ai_draft_payload"]["modules"][0]["summary"] == "已人工调整的一句话结论。"
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "reviewed"
    assert withdraw_response.status_code == 200
    assert withdraw_response.json()["status"] == "succeeded"


def test_degraded_narrative_requires_acknowledgement_before_approval(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.narratives.build_provider",
        lambda: MockNarrativeProvider(
            status=ProviderRunStatus.degraded,
            raw_suggestion="Hold",
            degraded_reasons=["news source unavailable"],
        ),
    )

    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token, "TNARR04")
        narrative_id = client.post(
            "/api/narratives/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "analysis_date": "2026-01-03"},
        ).json()["id"]

        blocked = client.post(
            f"/api/narratives/{narrative_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        acknowledged = client.post(
            f"/api/narratives/{narrative_id}/acknowledge-degraded",
            headers={"Authorization": f"Bearer {token}"},
        )
        approved = client.post(
            f"/api/narratives/{narrative_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )

    assert blocked.status_code == 400
    assert "acknowledged" in blocked.json()["detail"]
    assert acknowledged.status_code == 200
    assert acknowledged.json()["degraded_acknowledged_by"] == "admin"
    assert approved.status_code == 200
    assert approved.json()["status"] == "reviewed"


def test_regenerate_narrative(monkeypatch) -> None:
    providers = iter(
        [
            MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Hold"),
            MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Sell"),
        ]
    )
    monkeypatch.setattr("app.api.narratives.build_provider", lambda: next(providers))

    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token, "TNARR05")
        narrative_id = client.post(
            "/api/narratives/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "analysis_date": "2026-01-03"},
        ).json()["id"]
        response = client.post(
            f"/api/narratives/{narrative_id}/regenerate",
            headers={"Authorization": f"Bearer {token}"},
            json={"analysis_date": "2026-01-04"},
        )
        current = client.get(
            f"/api/narratives/backtests/{backtest_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = current.json()
    assert payload["id"] == narrative_id
    assert payload["analysis_date"] == "2026-01-04"
    assert payload["provider_raw_suggestion"] == "Sell"
