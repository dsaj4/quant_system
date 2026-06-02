from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import BacktestRun, Bar, Instrument, Portfolio, PortfolioInstrument, StrategyParameterSet, TaskStatus, User
from app.services.backtest import PortfolioLeg, run_portfolio_backtest, run_single_instrument_backtest
from app.services.operation_log import record_operation

router = APIRouter(prefix="/backtests", tags=["backtests"])


class BacktestCreate(BaseModel):
    instrument_id: int | None = None
    portfolio_id: int | None = None
    frequency: str = "5m"
    adjust: str | None = None
    parameter_set_id: int
    initial_cash: float = Field(default=100000, gt=0)


class BacktestRunResponse(BaseModel):
    id: int
    strategy_id: str
    parameter_set_id: int | None
    status: TaskStatus
    config: dict
    metrics: dict
    result_payload: dict
    message: str
    created_at: datetime


def backtest_response(backtest: BacktestRun) -> BacktestRunResponse:
    return BacktestRunResponse(
        id=backtest.id or 0,
        strategy_id=backtest.strategy_id,
        parameter_set_id=backtest.parameter_set_id,
        status=backtest.status,
        config=backtest.config,
        metrics=backtest.metrics,
        result_payload=backtest.result_payload,
        message=backtest.message,
        created_at=backtest.created_at,
    )


@router.get("", response_model=list[BacktestRunResponse])
def list_backtests(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> list[BacktestRunResponse]:
    statement = select(BacktestRun).order_by(BacktestRun.created_at.desc())
    return [backtest_response(backtest) for backtest in session.exec(statement).all()]


@router.post("", response_model=BacktestRunResponse)
def create_backtest(
    payload: BacktestCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> BacktestRunResponse:
    selected_scopes = [payload.instrument_id is not None, payload.portfolio_id is not None]
    if selected_scopes.count(True) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose exactly one backtest scope: instrument_id or portfolio_id",
        )

    parameter_set = session.get(StrategyParameterSet, payload.parameter_set_id)
    if not parameter_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown parameter set id: {payload.parameter_set_id}",
        )

    frequency = payload.frequency.strip().lower()
    adjust = payload.adjust.strip() if payload.adjust is not None else None
    scope_config: dict
    target_type: str
    target_id: str

    try:
        if payload.instrument_id is not None:
            instrument = session.get(Instrument, payload.instrument_id)
            if not instrument:
                raise ValueError(f"Unknown instrument id: {payload.instrument_id}")

            conditions = [Bar.instrument_id == payload.instrument_id, Bar.frequency == frequency]
            if adjust is not None:
                conditions.append(Bar.adjust == adjust)
            statement = select(Bar).where(*conditions).order_by(Bar.timestamp)
            bars = session.exec(statement).all()
            result = run_single_instrument_backtest(
                bars=bars,
                parameter_set=parameter_set,
                initial_cash=payload.initial_cash,
            )
            scope_config = {
                "scope": "instrument",
                "instrument_id": payload.instrument_id,
                "instrument_symbol": instrument.symbol,
            }
            target_type = "instrument"
            target_id = str(payload.instrument_id)
        else:
            portfolio = session.get(Portfolio, payload.portfolio_id)
            if not portfolio:
                raise ValueError(f"Unknown portfolio id: {payload.portfolio_id}")

            positions_statement = select(PortfolioInstrument).where(
                PortfolioInstrument.portfolio_id == payload.portfolio_id
            )
            positions = session.exec(positions_statement).all()
            legs: list[PortfolioLeg] = []
            for position in positions:
                instrument = session.get(Instrument, position.instrument_id)
                if not instrument:
                    raise ValueError(f"Unknown instrument id: {position.instrument_id}")

                conditions = [Bar.instrument_id == position.instrument_id, Bar.frequency == frequency]
                if adjust is not None:
                    conditions.append(Bar.adjust == adjust)
                bars_statement = select(Bar).where(*conditions).order_by(Bar.timestamp)
                legs.append(
                    PortfolioLeg(
                        instrument_id=position.instrument_id,
                        symbol=instrument.symbol,
                        weight=position.weight,
                        bars=session.exec(bars_statement).all(),
                    )
                )

            result = run_portfolio_backtest(
                legs=legs,
                parameter_set=parameter_set,
                initial_cash=payload.initial_cash,
            )
            scope_config = {
                "scope": "portfolio",
                "portfolio_id": payload.portfolio_id,
                "portfolio_name": portfolio.name,
                "positions": [
                    {"instrument_id": leg.instrument_id, "symbol": leg.symbol, "weight": leg.weight}
                    for leg in legs
                ],
            }
            target_type = "portfolio"
            target_id = str(payload.portfolio_id)
    except ValueError as exc:
        record_operation(
            session,
            action="backtest.create.failed",
            actor=current_user.username,
            target_type=target_type if "target_type" in locals() else "backtest_scope",
            target_id=target_id if "target_id" in locals() else "",
            detail={"message": str(exc), "frequency": frequency, "adjust": adjust},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    backtest = BacktestRun(
        strategy_id=parameter_set.strategy_id,
        parameter_set_id=parameter_set.id,
        status=TaskStatus.succeeded,
        config={
            **scope_config,
            "frequency": frequency,
            "adjust": adjust,
            "initial_cash": payload.initial_cash,
        },
        metrics=result.metrics,
        result_payload=result.result_payload,
        message="Backtest succeeded",
    )
    session.add(backtest)
    session.commit()
    session.refresh(backtest)

    record_operation(
        session,
        action="backtest.create.succeeded",
        actor=current_user.username,
        target_type="backtest_run",
        target_id=str(backtest.id),
        detail={**scope_config, "frequency": frequency, "adjust": adjust},
    )
    return backtest_response(backtest)
