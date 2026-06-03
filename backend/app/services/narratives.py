from copy import deepcopy
from datetime import date
from typing import Any

from sqlmodel import Session, select

from app.models import BacktestRun, NarrativeRun, NarrativeStatus, TaskStatus, utc_now
from app.services.narrative_inputs import build_narrative_input_summary
from app.services.narrative_provider import (
    CLIENT_NARRATIVE_DISCLAIMER,
    CLIENT_NARRATIVE_LABEL,
    NarrativeProvider,
    ProviderRunStatus,
    normalize_provider_result,
)
from app.services.narrative_rating import calculate_quant_rating
from app.services.operation_log import record_operation


ONE_LINER_LIMIT = 80
SUMMARY_LIMIT = 120
PARAGRAPH_LIMIT = 180
BULLET_LIMIT = 80
MAX_PARAGRAPHS = 3
MAX_BULLETS = 5


def _require_run(session: Session, narrative_id: int | None) -> NarrativeRun:
    run = session.get(NarrativeRun, narrative_id)
    if not run:
        raise ValueError(f"Unknown narrative id: {narrative_id}")
    return run


def _running_generation(session: Session, *, exclude_id: int | None = None) -> NarrativeRun | None:
    statement = select(NarrativeRun).where(NarrativeRun.status.in_([NarrativeStatus.pending, NarrativeStatus.running]))
    for run in session.exec(statement).all():
        if exclude_id is None or run.id != exclude_id:
            return run
    return None


def get_current_narrative_for_backtest(session: Session, backtest_id: int | None) -> NarrativeRun | None:
    statement = (
        select(NarrativeRun)
        .where(NarrativeRun.backtest_run_id == backtest_id)
        .order_by(NarrativeRun.updated_at.desc(), NarrativeRun.created_at.desc())
    )
    return session.exec(statement).first()


def _prepare_narrative_run(
    session: Session,
    backtest: BacktestRun,
    *,
    analysis_date: date,
    provider: NarrativeProvider,
    actor: str,
    today: date | None,
    is_smoke_test: bool,
    existing_run: NarrativeRun | None = None,
) -> NarrativeRun:
    if not provider.is_configured():
        raise ValueError("TradingAgents narrative provider is not configured")
    if backtest.status != TaskStatus.succeeded:
        raise ValueError("Only succeeded backtests can generate narrative")
    if _running_generation(session, exclude_id=existing_run.id if existing_run else None):
        raise ValueError("Another narrative generation is running")

    input_summary = build_narrative_input_summary(session, backtest, analysis_date, today=today)
    rating = calculate_quant_rating(backtest)
    run = existing_run or get_current_narrative_for_backtest(session, backtest.id)
    if not run:
        run = NarrativeRun(backtest_run_id=backtest.id or 0, analysis_date=analysis_date.isoformat())

    run.status = NarrativeStatus.pending
    run.is_smoke_test = is_smoke_test
    run.provider = "trading_agents"
    run.provider_model = ""
    run.analysis_date = analysis_date.isoformat()
    run.quant_rating = rating.rating.value
    run.quant_rating_inputs = rating.inputs
    run.target_scope = input_summary["target_scope"]
    run.target_summary = {"targets": input_summary["targets"], "target_label": input_summary.get("target_label")}
    run.ticker_mapping = input_summary["ticker_mapping"]
    run.coverage_summary = input_summary["coverage_summary"]
    run.input_summary = input_summary
    run.provider_structured_summary = {}
    run.provider_raw_suggestion = ""
    run.provider_conflict = False
    run.degraded_reasons = []
    run.degraded_acknowledged_by = ""
    run.degraded_acknowledged_at = None
    run.ai_draft_payload = {}
    run.reviewed_payload = {}
    run.reviewed_by = ""
    run.reviewed_at = None
    run.review_note = ""
    run.error_message = ""
    run.started_at = None
    run.finished_at = None
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)

    record_operation(
        session,
        action="narrative.generate.accepted",
        actor=actor,
        target_type="narrative_run",
        target_id=str(run.id),
        detail={"backtest_run_id": backtest.id, "analysis_date": run.analysis_date},
    )
    return run


def start_narrative_generation(
    session: Session,
    backtest_id: int | None,
    *,
    analysis_date: date,
    provider: NarrativeProvider,
    actor: str,
    today: date | None = None,
    is_smoke_test: bool = False,
) -> NarrativeRun:
    backtest = session.get(BacktestRun, backtest_id)
    if not backtest:
        raise ValueError(f"Unknown backtest id: {backtest_id}")
    return _prepare_narrative_run(
        session,
        backtest,
        analysis_date=analysis_date,
        provider=provider,
        actor=actor,
        today=today,
        is_smoke_test=is_smoke_test,
    )


def run_narrative_generation(session: Session, narrative_id: int | None, provider: NarrativeProvider) -> NarrativeRun:
    run = _require_run(session, narrative_id)
    run.status = NarrativeStatus.running
    run.started_at = utc_now()
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        provider_result = provider.run(run.input_summary)
        normalized = normalize_provider_result(
            provider_result,
            quant_rating=calculate_quant_rating(session.get(BacktestRun, run.backtest_run_id)).rating,
            input_summary=run.input_summary,
        )
    except RuntimeError as exc:
        run.status = NarrativeStatus.failed
        run.error_message = str(exc)
        run.finished_at = utc_now()
        run.updated_at = utc_now()
        session.add(run)
        session.commit()
        session.refresh(run)
        record_operation(
            session,
            action="narrative.generate.failed",
            target_type="narrative_run",
            target_id=str(run.id),
            detail={"message": run.error_message, "backtest_run_id": run.backtest_run_id},
        )
        return run

    run.status = NarrativeStatus.degraded if provider_result.status == ProviderRunStatus.degraded else NarrativeStatus.succeeded
    run.provider_model = normalized.provider_model
    run.provider_structured_summary = normalized.provider_structured_summary
    run.provider_raw_suggestion = normalized.provider_raw_suggestion
    run.provider_conflict = normalized.provider_conflict
    run.degraded_reasons = normalized.degraded_reasons
    run.ai_draft_payload = normalized.client_payload
    run.reviewed_payload = {}
    run.finished_at = utc_now()
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)

    record_operation(
        session,
        action="narrative.generate.degraded" if run.status == NarrativeStatus.degraded else "narrative.generate.succeeded",
        target_type="narrative_run",
        target_id=str(run.id),
        detail={"backtest_run_id": run.backtest_run_id, "degraded_reasons": run.degraded_reasons},
    )
    return run


def regenerate_narrative(
    session: Session,
    narrative_id: int | None,
    *,
    analysis_date: date,
    provider: NarrativeProvider,
    actor: str,
    today: date | None = None,
) -> NarrativeRun:
    run = _require_run(session, narrative_id)
    backtest = session.get(BacktestRun, run.backtest_run_id)
    if not backtest:
        raise ValueError(f"Unknown backtest id: {run.backtest_run_id}")
    return _prepare_narrative_run(
        session,
        backtest,
        analysis_date=analysis_date,
        provider=provider,
        actor=actor,
        today=today,
        is_smoke_test=run.is_smoke_test,
        existing_run=run,
    )


def save_narrative_draft(session: Session, narrative_id: int | None, payload: dict[str, Any]) -> NarrativeRun:
    run = _require_run(session, narrative_id)
    if run.status == NarrativeStatus.reviewed:
        raise ValueError("Narrative is reviewed; withdraw review before editing draft")
    run.ai_draft_payload = deepcopy(payload)
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def acknowledge_degraded(session: Session, narrative_id: int | None, *, actor: str) -> NarrativeRun:
    run = _require_run(session, narrative_id)
    if run.status != NarrativeStatus.degraded:
        raise ValueError("Only degraded narrative runs can be acknowledged")
    run.degraded_acknowledged_by = actor
    run.degraded_acknowledged_at = utc_now()
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)
    record_operation(
        session,
        action="narrative.degraded.acknowledged",
        actor=actor,
        target_type="narrative_run",
        target_id=str(run.id),
        detail={"backtest_run_id": run.backtest_run_id},
    )
    return run


def _payload_violations(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    modules = payload.get("modules") or []
    for module in modules:
        key = module.get("key")
        summary = str(module.get("summary") or "")
        if key == "one_liner" and len(summary) > ONE_LINER_LIMIT:
            violations.append(f"{key}.summary exceeds {ONE_LINER_LIMIT}")
        if len(summary) > SUMMARY_LIMIT:
            violations.append(f"{key}.summary exceeds {SUMMARY_LIMIT}")

        paragraphs = module.get("paragraphs") or []
        if len(paragraphs) > MAX_PARAGRAPHS:
            violations.append(f"{key}.paragraphs exceeds {MAX_PARAGRAPHS}")
        for index, paragraph in enumerate(paragraphs):
            if len(str(paragraph)) > PARAGRAPH_LIMIT:
                violations.append(f"{key}.paragraphs[{index}] exceeds {PARAGRAPH_LIMIT}")

        bullets = module.get("bullets") or []
        if len(bullets) > MAX_BULLETS:
            violations.append(f"{key}.bullets exceeds {MAX_BULLETS}")
        for index, bullet in enumerate(bullets):
            if len(str(bullet)) > BULLET_LIMIT:
                violations.append(f"{key}.bullets[{index}] exceeds {BULLET_LIMIT}")
    return violations


def approve_narrative_review(session: Session, narrative_id: int | None, *, actor: str, review_note: str = "") -> NarrativeRun:
    run = _require_run(session, narrative_id)
    if run.status == NarrativeStatus.degraded and not run.degraded_acknowledged_at:
        raise ValueError("Degraded narrative must be acknowledged before review")
    if run.status not in {NarrativeStatus.succeeded, NarrativeStatus.degraded}:
        raise ValueError("Only succeeded or degraded narratives can be reviewed")

    payload = run.ai_draft_payload or {}
    violations = _payload_violations(payload)
    if violations:
        raise ValueError("Narrative draft exceeds length limits: " + "; ".join(violations))

    reviewed_payload = {
        **payload,
        "enabled": True,
        "label": CLIENT_NARRATIVE_LABEL,
        "rating": run.quant_rating,
        "reviewed": True,
        "disclaimer": CLIENT_NARRATIVE_DISCLAIMER,
    }
    run.status = NarrativeStatus.reviewed
    run.reviewed_payload = reviewed_payload
    run.reviewed_by = actor
    run.reviewed_at = utc_now()
    run.review_note = review_note
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)
    record_operation(
        session,
        action="narrative.review.approved",
        actor=actor,
        target_type="narrative_run",
        target_id=str(run.id),
        detail={"backtest_run_id": run.backtest_run_id},
    )
    return run


def withdraw_narrative_review(session: Session, narrative_id: int | None, *, actor: str) -> NarrativeRun:
    run = _require_run(session, narrative_id)
    if run.status != NarrativeStatus.reviewed:
        raise ValueError("Only reviewed narratives can withdraw review")
    run.status = NarrativeStatus.degraded if run.degraded_reasons else NarrativeStatus.succeeded
    run.reviewed_payload = {}
    run.reviewed_by = ""
    run.reviewed_at = None
    run.review_note = ""
    run.updated_at = utc_now()
    session.add(run)
    session.commit()
    session.refresh(run)
    record_operation(
        session,
        action="narrative.review.withdrawn",
        actor=actor,
        target_type="narrative_run",
        target_id=str(run.id),
        detail={"backtest_run_id": run.backtest_run_id},
    )
    return run


def build_public_narrative_payload(run: NarrativeRun) -> dict[str, Any]:
    if run.status != NarrativeStatus.reviewed or not run.reviewed_payload:
        raise ValueError("Only reviewed narratives can build public payload")
    payload = {
        "enabled": True,
        "label": CLIENT_NARRATIVE_LABEL,
        "rating": run.quant_rating,
        "reviewed": True,
        "disclaimer": CLIENT_NARRATIVE_DISCLAIMER,
        "modules": run.reviewed_payload.get("modules") or [],
    }
    return payload
