from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import Bar, DataImportTask, Instrument, TaskStatus, User, utc_now
from app.services.data_quality import DataCompleteness, assess_bar_completeness
from app.services.market_data import fetch_public_bars, import_csv_bars
from app.services.operation_log import record_operation

router = APIRouter(prefix="/market-data", tags=["market-data"])


class CsvImportRequest(BaseModel):
    instrument_id: int
    frequency: str = Field(default="5m", min_length=1)
    adjust: str = ""
    source: str = "csv"
    csv_text: str = Field(min_length=1)


class PublicFetchRequest(BaseModel):
    instrument_id: int
    provider: str = "akshare"
    frequency: str = Field(default="5m", min_length=1)
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)
    adjust: str = ""


class DataImportTaskResponse(BaseModel):
    id: int
    source: str
    instrument_id: int | None
    frequency: str
    adjust: str
    status: TaskStatus
    message: str
    rows_imported: int
    rows_updated: int
    request_params: dict
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class BarResponse(BaseModel):
    id: int
    instrument_id: int
    frequency: str
    timestamp: datetime
    adjust: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    data_version: str


class DataCompletenessResponse(BaseModel):
    instrument_id: int
    frequency: str
    bar_count: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    expected_interval_minutes: int | None
    expected_bar_count: int | None
    missing_bar_count: int | None
    completeness_ratio: float | None
    gap_count: int
    largest_gap_minutes: float | None
    status: str
    message: str


def task_response(task: DataImportTask) -> DataImportTaskResponse:
    return DataImportTaskResponse(
        id=task.id or 0,
        source=task.source,
        instrument_id=task.instrument_id,
        frequency=task.frequency,
        adjust=task.adjust,
        status=task.status,
        message=task.message,
        rows_imported=task.rows_imported,
        rows_updated=task.rows_updated,
        request_params=task.request_params,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


def bar_response(bar: Bar) -> BarResponse:
    return BarResponse(
        id=bar.id or 0,
        instrument_id=bar.instrument_id,
        frequency=bar.frequency,
        timestamp=bar.timestamp,
        adjust=bar.adjust,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        source=bar.source,
        data_version=bar.data_version,
    )


@router.post("/import-csv", response_model=DataImportTaskResponse)
def import_csv_market_data(
    payload: CsvImportRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> DataImportTaskResponse:
    instrument = session.get(Instrument, payload.instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown instrument id: {payload.instrument_id}",
        )

    task = DataImportTask(
        source=payload.source.strip().lower() or "csv",
        status=TaskStatus.running,
        started_at=utc_now(),
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    frequency = payload.frequency.strip().lower()
    adjust = payload.adjust.strip()
    try:
        result = import_csv_bars(
            session,
            instrument_id=payload.instrument_id,
            frequency=frequency,
            source=task.source,
            csv_text=payload.csv_text,
            adjust=adjust,
        )
    except ValueError as exc:
        task.status = TaskStatus.failed
        task.finished_at = utc_now()
        task.message = str(exc)
        task.instrument_id = payload.instrument_id
        task.frequency = frequency
        task.adjust = adjust
        task.request_params = {"source": task.source, "adjust": adjust}
        session.add(task)
        session.commit()
        record_operation(
            session,
            action="market_data.import_csv.failed",
            actor=current_user.username,
            target_type="instrument",
            target_id=str(payload.instrument_id),
            detail={"frequency": frequency, "message": str(exc)},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    task.status = TaskStatus.succeeded
    task.finished_at = utc_now()
    task.message = "CSV import succeeded"
    task.instrument_id = payload.instrument_id
    task.frequency = frequency
    task.adjust = adjust
    task.rows_imported = result.rows_imported
    task.rows_updated = result.rows_updated
    task.request_params = {"source": task.source, "adjust": adjust}
    session.add(task)
    session.commit()
    session.refresh(task)

    record_operation(
        session,
        action="market_data.import_csv.succeeded",
        actor=current_user.username,
        target_type="instrument",
        target_id=str(payload.instrument_id),
        detail={
            "frequency": frequency,
            "rows_imported": result.rows_imported,
            "rows_updated": result.rows_updated,
        },
    )
    return task_response(task)


@router.post("/fetch-public", response_model=DataImportTaskResponse)
def fetch_public_market_data(
    payload: PublicFetchRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> DataImportTaskResponse:
    instrument = session.get(Instrument, payload.instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown instrument id: {payload.instrument_id}",
        )

    frequency = payload.frequency.strip().lower()
    adjust = payload.adjust.strip()
    provider = payload.provider.strip().lower() or "akshare"
    task = DataImportTask(
        source=provider,
        instrument_id=payload.instrument_id,
        frequency=frequency,
        adjust=adjust,
        request_params={
            "provider": provider,
            "start_date": payload.start_date.strip(),
            "end_date": payload.end_date.strip(),
            "adjust": adjust,
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
            instrument_id=payload.instrument_id,
            frequency=frequency,
            start_date=payload.start_date.strip(),
            end_date=payload.end_date.strip(),
            adjust=adjust,
            provider_name=provider,
        )
    except (RuntimeError, ValueError) as exc:
        task.status = TaskStatus.failed
        task.finished_at = utc_now()
        task.message = str(exc)
        session.add(task)
        session.commit()
        record_operation(
            session,
            action="market_data.fetch_public.failed",
            actor=current_user.username,
            target_type="instrument",
            target_id=str(payload.instrument_id),
            detail={"frequency": frequency, "message": str(exc), "source": provider, "adjust": adjust},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    task.status = TaskStatus.succeeded
    task.finished_at = utc_now()
    task.message = "Public data fetch succeeded"
    task.rows_imported = result.rows_imported
    task.rows_updated = result.rows_updated
    session.add(task)
    session.commit()
    session.refresh(task)

    record_operation(
        session,
        action="market_data.fetch_public.succeeded",
        actor=current_user.username,
        target_type="instrument",
        target_id=str(payload.instrument_id),
        detail={
            "frequency": frequency,
            "rows_imported": result.rows_imported,
            "rows_updated": result.rows_updated,
            "source": provider,
            "adjust": adjust,
        },
    )
    return task_response(task)


@router.get("/bars", response_model=list[BarResponse])
def list_bars(
    session: SessionDep,
    instrument_id: int = Query(gt=0),
    frequency: str = Query(min_length=1),
    adjust: str | None = Query(default=None),
    limit: int = Query(default=200, gt=0, le=1000),
    current_user: User = Depends(get_current_user),
) -> list[BarResponse]:
    conditions = [Bar.instrument_id == instrument_id, Bar.frequency == frequency.strip().lower()]
    if adjust is not None:
        conditions.append(Bar.adjust == adjust.strip())
    statement = select(Bar).where(*conditions).order_by(Bar.timestamp.desc()).limit(limit)
    bars = list(reversed(session.exec(statement).all()))
    return [bar_response(bar) for bar in bars]


def completeness_response(completeness: DataCompleteness) -> DataCompletenessResponse:
    return DataCompletenessResponse(
        instrument_id=completeness.instrument_id,
        frequency=completeness.frequency,
        bar_count=completeness.bar_count,
        first_timestamp=completeness.first_timestamp,
        last_timestamp=completeness.last_timestamp,
        expected_interval_minutes=completeness.expected_interval_minutes,
        expected_bar_count=completeness.expected_bar_count,
        missing_bar_count=completeness.missing_bar_count,
        completeness_ratio=completeness.completeness_ratio,
        gap_count=completeness.gap_count,
        largest_gap_minutes=completeness.largest_gap_minutes,
        status=completeness.status,
        message=completeness.message,
    )


@router.get("/completeness", response_model=DataCompletenessResponse)
def check_data_completeness(
    session: SessionDep,
    instrument_id: int = Query(gt=0),
    frequency: str = Query(min_length=1),
    adjust: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> DataCompletenessResponse:
    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown instrument id: {instrument_id}",
        )

    normalized_frequency = frequency.strip().lower()
    conditions = [Bar.instrument_id == instrument_id, Bar.frequency == normalized_frequency]
    if adjust is not None:
        conditions.append(Bar.adjust == adjust.strip())
    statement = select(Bar).where(*conditions).order_by(Bar.timestamp)
    return completeness_response(
        assess_bar_completeness(
            instrument_id=instrument_id,
            frequency=normalized_frequency,
            bars=session.exec(statement).all(),
        )
    )


@router.get("/import-tasks", response_model=list[DataImportTaskResponse])
def list_import_tasks(
    session: SessionDep,
    limit: int = Query(default=20, gt=0, le=100),
    current_user: User = Depends(get_current_user),
) -> list[DataImportTaskResponse]:
    statement = select(DataImportTask).order_by(DataImportTask.created_at.desc()).limit(limit)
    return [task_response(task) for task in session.exec(statement).all()]
