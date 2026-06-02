from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import Bar, Instrument, PaperRun, StrategyParameterSet, TaskStatus, User, utc_now
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
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


def paper_run_response(paper_run: PaperRun) -> PaperRunResponse:
    return PaperRunResponse(
        id=paper_run.id or 0,
        strategy_id=paper_run.strategy_id,
        status=paper_run.status,
        config=paper_run.config,
        latest_equity=paper_run.latest_equity,
        message=paper_run.message,
        started_at=paper_run.started_at,
        finished_at=paper_run.finished_at,
        created_at=paper_run.created_at,
    )


def append_state(config: dict, status_value: TaskStatus, message: str) -> dict:
    history = list(config.get("state_history") or [])
    history.append(
        {
            "status": status_value.value,
            "message": message,
            "at": utc_now().isoformat(),
        }
    )
    return {**config, "state_history": history}


def bar_snapshot(bars: list[Bar]) -> dict:
    return {
        "bar_count": len(bars),
        "first_timestamp": bars[0].timestamp.isoformat() if bars else None,
        "last_timestamp": bars[-1].timestamp.isoformat() if bars else None,
    }


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

    started_at = utc_now()
    base_config = append_state(
        {
            "instrument_id": payload.instrument_id,
            "instrument_symbol": instrument.symbol,
            "frequency": frequency,
            "adjust": adjust,
            "parameter_set_id": parameter_set.id,
            "initial_cash": payload.initial_cash,
            "data_snapshot": bar_snapshot(bars),
        },
        TaskStatus.pending,
        "Paper simulation accepted.",
    )
    paper_run = PaperRun(
        strategy_id=parameter_set.strategy_id,
        status=TaskStatus.pending,
        config=base_config,
        latest_equity=0,
        message="Paper simulation accepted",
        started_at=started_at,
    )
    session.add(paper_run)
    session.commit()
    session.refresh(paper_run)

    paper_run.status = TaskStatus.running
    paper_run.message = "Paper simulation running"
    paper_run.config = append_state(paper_run.config, TaskStatus.running, "Loaded market data and started simulation.")
    session.add(paper_run)
    session.commit()
    session.refresh(paper_run)

    try:
        result = run_single_instrument_paper_simulation(
            bars=bars,
            parameter_set=parameter_set,
            initial_cash=payload.initial_cash,
        )
    except ValueError as exc:
        paper_run.status = TaskStatus.failed
        paper_run.message = str(exc)
        paper_run.finished_at = utc_now()
        paper_run.config = append_state(
            {
                **paper_run.config,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
                "data_snapshot": bar_snapshot(bars),
            },
            TaskStatus.failed,
            str(exc),
        )
        session.add(paper_run)
        session.commit()
        session.refresh(paper_run)
        record_operation(
            session,
            action="paper_run.create.failed",
            actor=current_user.username,
            target_type="paper_run",
            target_id=str(paper_run.id),
            detail={
                "message": str(exc),
                "instrument_id": payload.instrument_id,
                "frequency": frequency,
                "adjust": adjust,
            },
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    latest_equity = float(result.metrics["latest_equity"])
    paper_run.status = TaskStatus.succeeded
    paper_run.latest_equity = latest_equity
    paper_run.message = "Paper simulation succeeded"
    paper_run.finished_at = utc_now()
    paper_run.config = append_state(
        {
            **paper_run.config,
            "metrics": result.metrics,
            "result_payload": result.result_payload,
            "paper_summary": result.result_payload.get("paper_summary", {}),
            "paper_signals": result.result_payload.get("paper_signals", []),
            "paper_trades": result.result_payload.get("paper_trades", []),
            "data_snapshot": bar_snapshot(bars),
        },
        TaskStatus.succeeded,
        "Paper simulation succeeded.",
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
