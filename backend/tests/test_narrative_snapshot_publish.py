from fastapi.testclient import TestClient

from app.main import app
from app.services.narrative_provider import MockNarrativeProvider, ProviderRunStatus
from backend.tests.test_snapshots import create_backtest, login_token


def generate_and_approve_narrative(client: TestClient, token: str, backtest_id: int, summary: str) -> int:
    generate_response = client.post(
        "/api/narratives/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"backtest_run_id": backtest_id, "analysis_date": "2026-01-03"},
    )
    assert generate_response.status_code == 200
    narrative_id = generate_response.json()["id"]

    current = client.get(
        f"/api/narratives/backtests/{backtest_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    draft = current["ai_draft_payload"]
    draft["modules"][0]["summary"] = summary
    draft["modules"][0]["paragraphs"] = [summary]

    update_response = client.patch(
        f"/api/narratives/{narrative_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": draft},
    )
    assert update_response.status_code == 200

    approve_response = client.post(
        f"/api/narratives/{narrative_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert approve_response.status_code == 200
    return narrative_id


def test_publish_with_reviewed_narrative_copies_public_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.narratives.build_provider",
        lambda: MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Buy"),
    )

    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token)
        generate_and_approve_narrative(client, token, backtest_id, "已审核叙事将固化进客户快照。")

        publish_response = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "Narrative report"},
        )

        assert publish_response.status_code == 200
        published = publish_response.json()
        payload = published["snapshot"]["immutable_payload"]
        public_response = client.get(f"/api/public/snapshots/{published['share_token']}")
        logs_response = client.get("/api/operation-logs", headers={"Authorization": f"Bearer {token}"})

    assert payload["narrative"]["label"] == "AI 投研参考结论"
    assert payload["narrative"]["reviewed"] is True
    assert payload["narrative"]["modules"][0]["summary"] == "已审核叙事将固化进客户快照。"
    serialized = str(payload["narrative"])
    assert "provider_raw_suggestion" not in serialized
    assert "degraded_reasons" not in serialized
    assert "reviewed_by" not in serialized
    assert "analysis_date" not in serialized
    assert public_response.status_code == 200
    assert public_response.json()["payload"]["narrative"]["modules"][0]["summary"] == "已审核叙事将固化进客户快照。"
    actions = [item["action"] for item in logs_response.json()]
    assert "narrative.publish.included" in actions


def test_snapshot_without_reviewed_narrative_still_publishes() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token)
        publish_response = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "No narrative report"},
        )

    assert publish_response.status_code == 200
    assert "narrative" not in publish_response.json()["snapshot"]["immutable_payload"]


def test_regenerating_after_publish_does_not_change_existing_snapshot(monkeypatch) -> None:
    providers = iter(
        [
            MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Hold"),
            MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Hold"),
        ]
    )
    monkeypatch.setattr("app.api.narratives.build_provider", lambda: next(providers))

    with TestClient(app) as client:
        token = login_token(client)
        backtest_id = create_backtest(client, token)
        narrative_id = generate_and_approve_narrative(client, token, backtest_id, "第一版已审核叙事。")

        first_publish = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "Narrative v1"},
        ).json()
        first_share_token = first_publish["share_token"]

        withdraw_response = client.post(
            f"/api/narratives/{narrative_id}/withdraw-review",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert withdraw_response.status_code == 200
        regenerate_response = client.post(
            f"/api/narratives/{narrative_id}/regenerate",
            headers={"Authorization": f"Bearer {token}"},
            json={"analysis_date": "2026-01-04"},
        )
        assert regenerate_response.status_code == 200
        current = client.get(
            f"/api/narratives/backtests/{backtest_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        draft = current["ai_draft_payload"]
        draft["modules"][0]["summary"] = "第二版已审核叙事。"
        draft["modules"][0]["paragraphs"] = ["第二版已审核叙事。"]
        client.patch(
            f"/api/narratives/{narrative_id}/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"payload": draft},
        )
        client.post(
            f"/api/narratives/{narrative_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        second_publish = client.post(
            "/api/snapshots/publish",
            headers={"Authorization": f"Bearer {token}"},
            json={"backtest_run_id": backtest_id, "title": "Narrative v2"},
        ).json()

        old_public = client.get(f"/api/public/snapshots/{first_share_token}").json()

    assert old_public["payload"]["narrative"]["modules"][0]["summary"] == "第一版已审核叙事。"
    assert second_publish["snapshot"]["version"] == first_publish["snapshot"]["version"] + 1
    assert second_publish["snapshot"]["immutable_payload"]["narrative"]["modules"][0]["summary"] == "第二版已审核叙事。"
