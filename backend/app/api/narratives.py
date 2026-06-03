from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.core.config import get_settings
from app.core.database import SessionDep, engine
from app.core.security import get_current_user
from app.models import NarrativeRun, NarrativeStatus, User
from app.services.narrative_provider import TradingAgentsNarrativeProvider
from app.services.narratives import (
    acknowledge_degraded,
    approve_narrative_review,
    get_current_narrative_for_backtest,
    regenerate_narrative,
    run_narrative_generation,
    save_narrative_draft,
    start_narrative_generation,
    withdraw_narrative_review,
)

router = APIRouter(prefix="/narratives", tags=["narratives"])


class NarrativeConfigResponse(BaseModel):
    enabled: bool
    configured: bool
    provider: str
    llm_provider: str
    model: str


class NarrativeGenerateRequest(BaseModel):
    backtest_run_id: int
    analysis_date: date
    is_smoke_test: bool = False


class NarrativeDraftUpdateRequest(BaseModel):
    payload: dict[str, Any]


class NarrativeApproveRequest(BaseModel):
    review_note: str = ""


class NarrativeRegenerateRequest(BaseModel):
    analysis_date: date


class NarrativeRunResponse(BaseModel):
    id: int
    backtest_run_id: int
    status: NarrativeStatus
    is_smoke_test: bool
    provider: str
    provider_model: str
    analysis_date: str
    quant_rating: str
    target_scope: str
    target_summary: dict
    ticker_mapping: dict
    coverage_summary: dict
    input_summary: dict
    provider_structured_summary: dict
    provider_raw_suggestion: str
    provider_conflict: bool
    degraded_reasons: list[str]
    degraded_acknowledged_by: str
    degraded_acknowledged_at: datetime | None
    ai_draft_payload: dict
    reviewed_payload: dict
    reviewed_by: str
    reviewed_at: datetime | None
    review_note: str
    error_message: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


def build_provider() -> TradingAgentsNarrativeProvider:
    return TradingAgentsNarrativeProvider(get_settings())


def narrative_response(run: NarrativeRun) -> NarrativeRunResponse:
    return NarrativeRunResponse(
        id=run.id or 0,
        backtest_run_id=run.backtest_run_id,
        status=run.status,
        is_smoke_test=run.is_smoke_test,
        provider=run.provider,
        provider_model=run.provider_model,
        analysis_date=run.analysis_date,
        quant_rating=run.quant_rating,
        target_scope=run.target_scope,
        target_summary=run.target_summary,
        ticker_mapping=run.ticker_mapping,
        coverage_summary=run.coverage_summary,
        input_summary=run.input_summary,
        provider_structured_summary=run.provider_structured_summary,
        provider_raw_suggestion=run.provider_raw_suggestion,
        provider_conflict=run.provider_conflict,
        degraded_reasons=run.degraded_reasons,
        degraded_acknowledged_by=run.degraded_acknowledged_by,
        degraded_acknowledged_at=run.degraded_acknowledged_at,
        ai_draft_payload=run.ai_draft_payload,
        reviewed_payload=run.reviewed_payload,
        reviewed_by=run.reviewed_by,
        reviewed_at=run.reviewed_at,
        review_note=run.review_note,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _run_generation_background(narrative_id: int, provider) -> None:
    with Session(engine) as session:
        run_narrative_generation(session, narrative_id, provider)


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/config", response_model=NarrativeConfigResponse)
def get_narrative_config(current_user: User = Depends(get_current_user)) -> NarrativeConfigResponse:
    settings = get_settings()
    provider = build_provider()
    return NarrativeConfigResponse(
        enabled=settings.trading_agents_enabled,
        configured=provider.is_configured(),
        provider="trading_agents",
        llm_provider=settings.trading_agents_llm_provider,
        model=settings.trading_agents_deep_think_llm,
    )


@router.post("/generate", response_model=NarrativeRunResponse)
def generate_narrative(
    payload: NarrativeGenerateRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    provider = build_provider()
    try:
        run = start_narrative_generation(
            session,
            payload.backtest_run_id,
            analysis_date=payload.analysis_date,
            provider=provider,
            actor=current_user.username,
            is_smoke_test=payload.is_smoke_test,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc

    background_tasks.add_task(_run_generation_background, run.id or 0, provider)
    return narrative_response(run)


@router.get("/backtests/{backtest_id}", response_model=NarrativeRunResponse)
def get_narrative_for_backtest(
    backtest_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    run = get_current_narrative_for_backtest(session, backtest_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narrative not found")
    return narrative_response(run)


@router.patch("/{narrative_id}/draft", response_model=NarrativeRunResponse)
def update_narrative_draft(
    narrative_id: int,
    payload: NarrativeDraftUpdateRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    try:
        run = save_narrative_draft(session, narrative_id, payload.payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return narrative_response(run)


@router.post("/{narrative_id}/acknowledge-degraded", response_model=NarrativeRunResponse)
def acknowledge_narrative_degraded(
    narrative_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    try:
        run = acknowledge_degraded(session, narrative_id, actor=current_user.username)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return narrative_response(run)


@router.post("/{narrative_id}/approve", response_model=NarrativeRunResponse)
def approve_narrative(
    narrative_id: int,
    payload: NarrativeApproveRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    try:
        run = approve_narrative_review(
            session,
            narrative_id,
            actor=current_user.username,
            review_note=payload.review_note,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return narrative_response(run)


@router.post("/{narrative_id}/withdraw-review", response_model=NarrativeRunResponse)
def withdraw_narrative(
    narrative_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    try:
        run = withdraw_narrative_review(session, narrative_id, actor=current_user.username)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return narrative_response(run)


@router.post("/{narrative_id}/regenerate", response_model=NarrativeRunResponse)
def regenerate_narrative_run(
    narrative_id: int,
    payload: NarrativeRegenerateRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> NarrativeRunResponse:
    provider = build_provider()
    try:
        run = regenerate_narrative(
            session,
            narrative_id,
            analysis_date=payload.analysis_date,
            provider=provider,
            actor=current_user.username,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc

    background_tasks.add_task(_run_generation_background, run.id or 0, provider)
    return narrative_response(run)
