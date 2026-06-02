from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.core.database import engine
from app.models import DataImportTask, Instrument, MarketDataSchedule, TaskStatus, utc_now
from app.services.market_data import fetch_public_bars
from app.services.operation_log import record_operation

SCHEDULE_JOB_PREFIX = "market-data-schedule-"
scheduler = BackgroundScheduler()


@dataclass(frozen=True)
class ScheduleExecutionResult:
    task_id: int
    status: TaskStatus
    message: str


def job_id(schedule_id: int) -> str:
    return f"{SCHEDULE_JOB_PREFIX}{schedule_id}"


def execute_market_data_schedule(schedule_id: int) -> ScheduleExecutionResult:
    with Session(engine) as session:
        schedule = session.get(MarketDataSchedule, schedule_id)
        if not schedule or not schedule.is_active:
            raise ValueError("Market data schedule is inactive or missing")

        instrument = session.get(Instrument, schedule.instrument_id)
        if not instrument:
            raise ValueError("Scheduled instrument not found")

        task = DataImportTask(
            source=schedule.provider,
            instrument_id=schedule.instrument_id,
            frequency=schedule.frequency,
            adjust=schedule.adjust,
            request_params={
                "provider": schedule.provider,
                "start_date": schedule.start_date,
                "end_date": schedule.end_date,
                "adjust": schedule.adjust,
                "schedule_id": schedule.id,
            },
            status=TaskStatus.running,
            started_at=utc_now(),
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        try:
            result = fetch_public_bars(
                session,
                instrument_symbol=instrument.symbol,
                instrument_exchange=instrument.exchange,
                instrument_id=instrument.id or 0,
                frequency=schedule.frequency,
                start_date=schedule.start_date,
                end_date=schedule.end_date,
                adjust=schedule.adjust,
                provider_name=schedule.provider,
            )
            task.status = TaskStatus.succeeded
            task.message = "Scheduled public data fetch succeeded"
            task.rows_imported = result.rows_imported
            task.rows_updated = result.rows_updated
            action = "market_data.schedule.run.succeeded"
        except (RuntimeError, ValueError) as exc:
            task.status = TaskStatus.failed
            task.message = str(exc)
            action = "market_data.schedule.run.failed"

        task.finished_at = utc_now()
        schedule.last_run_at = task.finished_at
        schedule.last_status = task.status
        schedule.last_message = task.message
        session.add(task)
        session.add(schedule)
        session.commit()
        session.refresh(task)

        record_operation(
            session,
            action=action,
            actor="scheduler",
            target_type="market_data_schedule",
            target_id=str(schedule.id),
            detail={
                "instrument_id": schedule.instrument_id,
                "provider": schedule.provider,
                "frequency": schedule.frequency,
                "adjust": schedule.adjust,
            },
        )
        return ScheduleExecutionResult(
            task_id=task.id or 0,
            status=task.status,
            message=schedule.last_message,
        )


def register_market_data_schedule(schedule: MarketDataSchedule) -> None:
    if not schedule.id or not schedule.is_active:
        return
    scheduler.add_job(
        execute_market_data_schedule,
        trigger="interval",
        minutes=schedule.interval_minutes,
        args=[schedule.id],
        id=job_id(schedule.id),
        replace_existing=True,
    )


def remove_market_data_schedule(schedule_id: int) -> None:
    if scheduler.get_job(job_id(schedule_id)):
        scheduler.remove_job(job_id(schedule_id))


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.start()
    with Session(engine) as session:
        statement = select(MarketDataSchedule).where(MarketDataSchedule.is_active == True)  # noqa: E712
        for schedule in session.exec(statement).all():
            register_market_data_schedule(schedule)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
