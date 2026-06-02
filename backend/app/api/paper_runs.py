from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import Bar, Instrument, PaperRun, StrategyParameterSet, TaskStatus, User
from app.services.operation_log import record_operation
from app.services.paper import run_single_instrument_paper_simulation

router = APIRouter(prefix="/paper-runs", tags=["paper runs"])


class PaperRunCreate(BaseModel):
    instrument_id: int
    frequency: str = "5m"
    adjust: str | None = None
    parameter_set_id: int
    initial_cash: float = Field(default=100000, gt=0)


class PaperRunResponse(BaseModel):
    id: int
    strategy_id: str
    status: TaskStatus
    config: dict
    latest_equity: float
    message: str
    created_at: datetime


def paper_run_response(paper_run: PaperRun) -> PaperRunResponse:
    return PaperRunResponse(
        id=paper_run.id or 0,
        strategy_id=paper_run.strategy_id,
        status=paper_run.status,
        config=paper_run.config,
        latest_equity=paper_run.latest_equity,
        message=paper_run.message,
        created_at=paper_run.created_at,
    )


@router.get("", response_model=list[PaperRunResponse])
def list_paper_runs(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> list[PaperRunResponse]:
    statement = select(PaperRun).order_by(PaperRun.created_at.desc())
    return [paper_run_response(paper_run) for paper_run in session.exec(statement).all()]


@router.post("", response_model=PaperRunResponse)
def create_paper_run(
    payload: PaperRunCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> PaperRunResponse:
    instrument = session.get(Instrument, payload.instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown instrument id: {payload.instrument_id}",
        )

    parameter_set = session.get(StrategyParameterSet, payload.parameter_set_id)
    if not parameter_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown parameter set id: {payload.parameter_set_id}",
        )

    frequency = payload.frequency.strip().lower()
    adjust = payload.adjust.strip() if payload.adjust is not None else None
    conditions = [Bar.instrument_id == payload.instrument_id, Bar.frequency == frequency]
    if adjust is not None:
        conditions.append(Bar.adjust == adjust)
    statement = select(Bar).where(*conditions).order_by(Bar.timestamp)
    bars = session.exec(statement).all()

    try:
        result = run_single_instrument_paper_simulation(
            bars=bars,
            parameter_set=parameter_set,
            initial_cash=payload.initial_cash,
        )
    except ValueError as exc:
        record_operation(
            session,
            action="paper_run.create.failed",
            actor=current_user.username,
            target_type="instrument",
            target_id=str(payload.instrument_id),
            detail={"message": str(exc), "frequency": frequency, "adjust": adjust},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    latest_equity = float(result.metrics["latest_equity"])
    paper_run = PaperRun(
        strategy_id=parameter_set.strategy_id,
        status=TaskStatus.succeeded,
        config={
            "instrument_id": payload.instrument_id,
            "frequency": frequency,
            "adjust": adjust,
            "parameter_set_id": parameter_set.id,
            "initial_cash": payload.initial_cash,
            "metrics": result.metrics,
            "result_payload": result.result_payload,
        },
        latest_equity=latest_equity,
        message="Paper simulation succeeded",
    )
    session.add(paper_run)
    session.commit()
    session.refresh(paper_run)

    record_operation(
        session,
        action="paper_run.create.succeeded",
        actor=current_user.username,
        target_type="paper_run",
        target_id=str(paper_run.id),
        detail={"instrument_id": payload.instrument_id, "frequency": frequency, "adjust": adjust},
    )
    return paper_run_response(paper_run)
