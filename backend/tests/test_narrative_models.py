from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import BacktestRun, NarrativeRun, NarrativeStatus, TaskStatus


def test_narrative_status_values_cover_review_workflow() -> None:
    assert {status.value for status in NarrativeStatus} == {
        "pending",
        "running",
        "succeeded",
        "degraded",
        "failed",
        "reviewed",
    }


def test_narrative_run_table_has_required_columns() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    inspector = inspect(engine)
    assert "narrativerun" in inspector.get_table_names()

    columns = {column["name"] for column in inspector.get_columns("narrativerun")}
    assert {
        "id",
        "backtest_run_id",
        "status",
        "is_smoke_test",
        "provider",
        "provider_model",
        "analysis_date",
        "quant_rating",
        "quant_rating_inputs",
        "target_scope",
        "target_summary",
        "ticker_mapping",
        "coverage_summary",
        "input_summary",
        "provider_structured_summary",
        "provider_raw_suggestion",
        "provider_conflict",
        "degraded_reasons",
        "degraded_acknowledged_by",
        "degraded_acknowledged_at",
        "ai_draft_payload",
        "reviewed_payload",
        "reviewed_by",
        "reviewed_at",
        "review_note",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_narrative_run_json_payloads_round_trip() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        backtest = BacktestRun(
            strategy_id="dual_ma",
            status=TaskStatus.succeeded,
            metrics={"cumulative_return": 0.12},
            result_payload={"data_quality": {"status": "ok"}},
        )
        session.add(backtest)
        session.commit()
        session.refresh(backtest)

        run = NarrativeRun(
            backtest_run_id=backtest.id,
            status=NarrativeStatus.succeeded,
            analysis_date="2026-06-03",
            quant_rating="neutral",
            quant_rating_inputs={"max_drawdown": -0.08},
            target_scope="instrument",
            target_summary={"symbol": "600519", "exchange": "SH"},
            ticker_mapping={"600519.SH": "600519.SS"},
            coverage_summary={"covered": ["600519.SS"]},
            input_summary={"backtest_id": backtest.id},
            provider_structured_summary={"technical": "trend intact"},
            provider_raw_suggestion="Buy",
            provider_conflict=True,
            degraded_reasons=["news source unavailable"],
            ai_draft_payload={"modules": [{"key": "one_liner"}]},
            reviewed_payload={"rating": "neutral", "modules": []},
        )
        session.add(run)
        session.commit()

        saved = session.exec(select(NarrativeRun)).one()

    assert saved.status == NarrativeStatus.succeeded
    assert saved.quant_rating_inputs["max_drawdown"] == -0.08
    assert saved.ticker_mapping["600519.SH"] == "600519.SS"
    assert saved.ai_draft_payload["modules"][0]["key"] == "one_liner"
    assert saved.reviewed_payload["rating"] == "neutral"
