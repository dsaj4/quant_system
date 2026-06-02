from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import Instrument, MarketDataSchedule, TaskStatus, User
from app.scheduler.market_data import execute_market_data_schedule, register_market_data_schedule, remove_market_data_schedule
from app.services.operation_log import record_operation

router = APIRouter(prefix="/market-data-schedules", tags=["market-data-schedules"])


class MarketDataScheduleCreate(BaseModel):
    instrument_id: int
    provider: str = "tushare"
    frequency: str = Field(default="5m", min_length=1)
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)
    adjust: str = ""
    interval_minutes: int = Field(default=60, ge=1, le=1440)


class MarketDataScheduleResponse(BaseModel):
    id: int
    instrument_id: int
    provider: str
    frequency: str
    start_date: str
    end_date: str
    adjust: str
    interval_minutes: int
    is_active: bool
    last_run_at: datetime | None
    last_status: TaskStatus | None
    last_message: str
    created_at: datetime


class ScheduleRunResponse(BaseModel):
    task_id: int
    status: TaskStatus
    message: str


def schedule_response(schedule: MarketDataSchedule) -> MarketDataScheduleResponse:
    return MarketDataScheduleResponse(
        id=schedule.id or 0,
        instrument_id=schedule.instrument_id,
        provider=schedule.provider,
        frequency=schedule.frequency,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        adjust=schedule.adjust,
        interval_minutes=schedule.interval_minutes,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        last_status=schedule.last_status,
        last_message=schedule.last_message,
        created_at=schedule.created_at,
    )


@router.get("", response_model=list[MarketDataScheduleResponse])
def list_market_data_schedules(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> list[MarketDataScheduleResponse]:
    statement = select(MarketDataSchedule).order_by(MarketDataSchedule.created_at.desc())
    return [schedule_response(schedule) for schedule in session.exec(statement).all()]


@router.post("", response_model=MarketDataScheduleResponse)
def create_market_data_schedule(
    payload: MarketDataScheduleCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> MarketDataScheduleResponse:
    instrument = session.get(Instrument, payload.instrument_id)
    if not instrument:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown instrument")

    schedule = MarketDataSchedule(
        instrument_id=payload.instrument_id,
        provider=payload.provider.strip().lower() or "tushare",
        frequency=payload.frequency.strip().lower(),
        start_date=payload.start_date.strip(),
        end_date=payload.end_date.strip(),
        adjust=payload.adjust.strip(),
        interval_minutes=payload.interval_minutes,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    register_market_data_schedule(schedule)
    record_operation(
        session,
        action="market_data.schedule.create",
        actor=current_user.username,
        target_type="market_data_schedule",
        target_id=str(schedule.id),
        detail={
            "instrument_id": schedule.instrument_id,
            "provider": schedule.provider,
            "interval_minutes": schedule.interval_minutes,
        },
    )
    return schedule_response(schedule)


@router.post("/{schedule_id}/run-now", response_model=ScheduleRunResponse)
def run_market_data_schedule_now(
    schedule_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> ScheduleRunResponse:
    schedule = session.get(MarketDataSchedule, schedule_id)
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active schedule not found")

    result = execute_market_data_schedule(schedule_id)
    return ScheduleRunResponse(task_id=result.task_id, status=result.status, message=result.message)


@router.post("/{schedule_id}/disable", response_model=MarketDataScheduleResponse)
def disable_market_data_schedule(
    schedule_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> MarketDataScheduleResponse:
    schedule = session.get(MarketDataSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    schedule.is_active = False
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    remove_market_data_schedule(schedule_id)
    record_operation(
        session,
        action="market_data.schedule.disable",
        actor=current_user.username,
        target_type="market_data_schedule",
        target_id=str(schedule.id),
        detail={},
    )
    return schedule_response(schedule)
