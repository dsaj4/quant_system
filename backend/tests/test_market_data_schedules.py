from fastapi.testclient import TestClient

from app.main import app
from app.models import TaskStatus
from app.scheduler.market_data import ScheduleExecutionResult
from app.scheduler.market_data import job_id, scheduler


def login_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_instrument(client: TestClient, token: str) -> int:
    response = client.post(
        "/api/instruments",
        headers={"Authorization": f"Bearer {token}"},
        json={"symbol": "TSCHED01", "exchange": "SH", "name": "Schedule Test", "asset_type": "stock"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_admin_can_create_run_and_disable_market_data_schedule(monkeypatch) -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token)

        create_response = client.post(
            "/api/market-data-schedules",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "start_date": "2026-01-02 09:30:00",
                "end_date": "2026-01-02 15:00:00",
                "interval_minutes": 30,
            },
        )
        assert create_response.status_code == 200
        schedule = create_response.json()
        schedule_id = schedule["id"]
        assert schedule["is_active"] is True
        assert schedule["provider"] == "tushare"
        assert schedule["interval_minutes"] == 30
        assert scheduler.get_job(job_id(schedule_id))

        list_response = client.get(
            "/api/market-data-schedules",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == schedule_id

        def fake_execute_schedule(schedule_id: int) -> ScheduleExecutionResult:
            return ScheduleExecutionResult(
                task_id=9876,
                status=TaskStatus.succeeded,
                message="Scheduled fetch succeeded",
            )

        monkeypatch.setattr("app.api.market_data_schedules.execute_market_data_schedule", fake_execute_schedule)
        run_response = client.post(
            f"/api/market-data-schedules/{schedule_id}/run-now",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert run_response.status_code == 200
        assert run_response.json()["status"] == "succeeded"

        disable_response = client.post(
            f"/api/market-data-schedules/{schedule_id}/disable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["is_active"] is False
        assert scheduler.get_job(job_id(schedule_id)) is None

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "market_data.schedule.create" in actions
        assert "market_data.schedule.disable" in actions
