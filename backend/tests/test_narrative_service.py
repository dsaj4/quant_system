import time
from copy import deepcopy
from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import BacktestRun, Instrument, NarrativeRun, NarrativeStatus, OperationLog, TaskStatus
from app.services.narrative_provider import MockNarrativeProvider, ProviderRunStatus
from app.services.narratives import (
    acknowledge_degraded,
    approve_narrative_review,
    build_public_narrative_payload,
    get_current_narrative_for_backtest,
    regenerate_narrative,
    run_narrative_generation,
    save_narrative_draft,
    start_narrative_generation,
    withdraw_narrative_review,
)


class DisabledProvider(MockNarrativeProvider):
    def is_configured(self) -> bool:
        return False


class SlowProvider(MockNarrativeProvider):
    def run(self, input_summary):
        time.sleep(0.05)
        return super().run(input_summary)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def add_instrument_backtest(
    session: Session,
    *,
    exchange: str = "SH",
    status: TaskStatus = TaskStatus.succeeded,
) -> BacktestRun:
    instrument = Instrument(symbol="600519", exchange=exchange, name="贵州茅台")
    session.add(instrument)
    session.commit()
    session.refresh(instrument)
    backtest = BacktestRun(
        strategy_id="rolling_t_grid",
        status=status,
        config={"scope": "instrument", "instrument_id": instrument.id, "instrument_symbol": instrument.symbol},
        metrics={
            "cumulative_return": 0.12,
            "max_drawdown": -0.06,
            "sharpe_ratio": 1.1,
            "return_drawdown_ratio": 2.0,
            "bar_count": 60,
            "trade_count": 4,
        },
        result_payload={
            "equity_curve": [
                {"timestamp": "2026-01-02T09:35:00", "value": 100000},
                {"timestamp": "2026-01-31T15:00:00", "value": 112000},
            ],
            "data_quality": {"status": "ok", "warnings": []},
        },
    )
    session.add(backtest)
    session.commit()
    session.refresh(backtest)
    return backtest


def generated_run(session: Session, provider: MockNarrativeProvider | None = None) -> NarrativeRun:
    backtest = add_instrument_backtest(session)
    run = start_narrative_generation(
        session,
        backtest.id,
        analysis_date=date(2026, 2, 1),
        provider=provider or MockNarrativeProvider(raw_suggestion="Hold"),
        actor="admin",
        today=date(2026, 6, 3),
    )
    return run_narrative_generation(session, run.id, provider or MockNarrativeProvider(raw_suggestion="Hold"))


def test_cannot_generate_when_provider_disabled() -> None:
    with make_session() as session:
        backtest = add_instrument_backtest(session)

        with pytest.raises(ValueError, match="not configured"):
            start_narrative_generation(
                session,
                backtest.id,
                analysis_date=date(2026, 2, 1),
                provider=DisabledProvider(),
                actor="admin",
                today=date(2026, 6, 3),
            )


def test_cannot_generate_from_missing_or_non_succeeded_backtest() -> None:
    with make_session() as session:
        with pytest.raises(ValueError, match="Unknown backtest"):
            start_narrative_generation(
                session,
                999,
                analysis_date=date(2026, 2, 1),
                provider=MockNarrativeProvider(),
                actor="admin",
                today=date(2026, 6, 3),
            )

        backtest = add_instrument_backtest(session, status=TaskStatus.failed)
        with pytest.raises(ValueError, match="Only succeeded backtests"):
            start_narrative_generation(
                session,
                backtest.id,
                analysis_date=date(2026, 2, 1),
                provider=MockNarrativeProvider(),
                actor="admin",
                today=date(2026, 6, 3),
            )


def test_cannot_generate_when_ticker_mapping_fails() -> None:
    with make_session() as session:
        backtest = add_instrument_backtest(session, exchange="NASDAQ")

        with pytest.raises(ValueError, match="Unsupported exchange"):
            start_narrative_generation(
                session,
                backtest.id,
                analysis_date=date(2026, 2, 1),
                provider=MockNarrativeProvider(),
                actor="admin",
                today=date(2026, 6, 3),
            )


def test_global_running_task_rejects_new_generation_request() -> None:
    with make_session() as session:
        first = add_instrument_backtest(session)
        second = add_instrument_backtest(session)
        session.add(
            NarrativeRun(
                backtest_run_id=first.id,
                status=NarrativeStatus.running,
                analysis_date="2026-02-01",
                quant_rating="neutral",
            )
        )
        session.commit()

        with pytest.raises(ValueError, match="Another narrative generation is running"):
            start_narrative_generation(
                session,
                second.id,
                analysis_date=date(2026, 2, 1),
                provider=MockNarrativeProvider(),
                actor="admin",
                today=date(2026, 6, 3),
            )


def test_generation_flows_to_succeeded_and_logs_operation() -> None:
    with make_session() as session:
        run = generated_run(session, MockNarrativeProvider(status=ProviderRunStatus.succeeded, raw_suggestion="Buy"))

        assert run.status == NarrativeStatus.succeeded
        assert run.ai_draft_payload["rating"] == "positive"
        assert run.provider_raw_suggestion == "Buy"
        assert run.provider_conflict is False
        assert get_current_narrative_for_backtest(session, run.backtest_run_id).id == run.id
        actions = [log.action for log in session.exec(select(OperationLog)).all()]
        assert "narrative.generate.succeeded" in actions


def test_generation_can_finish_as_degraded_or_failed() -> None:
    with make_session() as session:
        degraded = generated_run(
            session,
            MockNarrativeProvider(
                status=ProviderRunStatus.degraded,
                raw_suggestion="Hold",
                degraded_reasons=["news source unavailable"],
            ),
        )
        assert degraded.status == NarrativeStatus.degraded
        assert degraded.degraded_reasons == ["news source unavailable"]

    with make_session() as session:
        backtest = add_instrument_backtest(session)
        provider = MockNarrativeProvider(status=ProviderRunStatus.failed, error_message="provider failed")
        run = start_narrative_generation(
            session,
            backtest.id,
            analysis_date=date(2026, 2, 1),
            provider=provider,
            actor="admin",
            today=date(2026, 6, 3),
        )
        failed = run_narrative_generation(session, run.id, provider)
        assert failed.status == NarrativeStatus.failed
        assert failed.error_message == "provider failed"


def test_generation_timeout_marks_run_failed_and_releases_running_lock() -> None:
    with make_session() as session:
        backtest = add_instrument_backtest(session)
        provider = SlowProvider()
        run = start_narrative_generation(
            session,
            backtest.id,
            analysis_date=date(2026, 2, 1),
            provider=provider,
            actor="admin",
            today=date(2026, 6, 3),
        )

        failed = run_narrative_generation(session, run.id, provider, timeout_seconds=0.01)

        assert failed.status == NarrativeStatus.failed
        assert "timed out" in failed.error_message
        replacement = start_narrative_generation(
            session,
            backtest.id,
            analysis_date=date(2026, 2, 1),
            provider=MockNarrativeProvider(),
            actor="admin",
            today=date(2026, 6, 3),
        )
        assert replacement.status == NarrativeStatus.pending


def test_degraded_run_must_be_acknowledged_before_review() -> None:
    with make_session() as session:
        run = generated_run(
            session,
            MockNarrativeProvider(status=ProviderRunStatus.degraded, degraded_reasons=["partial data unavailable"]),
        )
        save_narrative_draft(session, run.id, run.ai_draft_payload)

        with pytest.raises(ValueError, match="acknowledged"):
            approve_narrative_review(session, run.id, actor="admin")

        acknowledged = acknowledge_degraded(session, run.id, actor="admin")
        assert acknowledged.degraded_acknowledged_by == "admin"
        reviewed = approve_narrative_review(session, run.id, actor="admin")
        assert reviewed.status == NarrativeStatus.reviewed


def test_over_limit_draft_can_save_but_cannot_review() -> None:
    with make_session() as session:
        run = generated_run(session)
        payload = deepcopy(run.ai_draft_payload)
        payload["modules"][0]["summary"] = "过" * 121
        saved = save_narrative_draft(session, run.id, payload)

        assert saved.ai_draft_payload["modules"][0]["summary"] == "过" * 121
        with pytest.raises(ValueError, match="length limits"):
            approve_narrative_review(session, run.id, actor="admin")


def test_reviewed_payload_is_read_only_until_withdrawn() -> None:
    with make_session() as session:
        run = generated_run(session)
        approve_narrative_review(session, run.id, actor="admin")

        with pytest.raises(ValueError, match="withdraw review"):
            save_narrative_draft(session, run.id, run.ai_draft_payload)

        withdrawn = withdraw_narrative_review(session, run.id, actor="admin")
        assert withdrawn.status == NarrativeStatus.succeeded
        saved = save_narrative_draft(session, run.id, run.ai_draft_payload)
        assert saved.status == NarrativeStatus.succeeded


def test_regenerate_replaces_latest_draft_for_backtest() -> None:
    with make_session() as session:
        backtest = add_instrument_backtest(session)
        first = start_narrative_generation(
            session,
            backtest.id,
            analysis_date=date(2026, 2, 1),
            provider=MockNarrativeProvider(raw_suggestion="Hold"),
            actor="admin",
            today=date(2026, 6, 3),
        )
        run_narrative_generation(session, first.id, MockNarrativeProvider(raw_suggestion="Hold"))

        regenerated = regenerate_narrative(
            session,
            first.id,
            analysis_date=date(2026, 2, 2),
            provider=MockNarrativeProvider(raw_suggestion="Sell"),
            actor="admin",
            today=date(2026, 6, 3),
        )
        run_narrative_generation(session, regenerated.id, MockNarrativeProvider(raw_suggestion="Sell"))
        session.refresh(regenerated)

        assert regenerated.id == first.id
        assert regenerated.analysis_date == "2026-02-02"
        assert regenerated.provider_raw_suggestion == "Sell"
        assert len(session.exec(select(NarrativeRun)).all()) == 1


def test_public_payload_contains_only_reviewed_client_narrative() -> None:
    with make_session() as session:
        run = generated_run(session, MockNarrativeProvider(raw_suggestion="Buy"))
        reviewed = approve_narrative_review(session, run.id, actor="admin")

        payload = build_public_narrative_payload(reviewed)

    assert payload["enabled"] is True
    assert payload["reviewed"] is True
    assert payload["label"] == "AI 投研参考结论"
    assert "provider_raw_suggestion" not in payload
    assert "degraded_reasons" not in payload
    assert "reviewed_by" not in payload
    assert "analysis_date" not in payload
