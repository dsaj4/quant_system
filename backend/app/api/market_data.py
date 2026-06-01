from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.database import SessionDep
from app.core.security import get_current_user
from app.models import Bar, DataImportTask, Instrument, TaskStatus, User, utc_now
from app.services.market_data import fetch_public_bars, import_csv_bars
from app.services.operation_log import record_operation

router = APIRouter(prefix="/market-data", tags=["market-data"])


class CsvImportRequest(BaseModel):
    instrument_id: int
    frequency: str = Field(default="5m", min_length=1)
    source: str = "csv"
    csv_text: str = Field(min_length=1)


class PublicFetchRequest(BaseModel):
    instrument_id: int
    frequency: str = Field(default="5m", min_length=1)
    start_date: str = Field(min_length=1)
    end_date: str = Field(min_length=1)
    adjust: str = ""


class DataImportTaskResponse(BaseModel):
    id: int
    source: str
    status: TaskStatus
    message: str
    rows_imported: int
    rows_updated: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class BarResponse(BaseModel):
    id: int
    instrument_id: int
    frequency: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    data_version: str


def task_response(task: DataImportTask) -> DataImportTaskResponse:
    detail = {}
    if task.message.startswith("{"):
        # Keep the table model stable for now; row counts live in the response/log detail.
        import json

        detail = json.loads(task.message)

    return DataImportTaskResponse(
        id=task.id or 0,
        source=task.source,
        status=task.status,
        message=detail.get("message", task.message),
        rows_imported=int(detail.get("rows_imported", 0)),
        rows_updated=int(detail.get("rows_updated", 0)),
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

    import json

    task = DataImportTask(
        source=payload.source.strip().lower() or "csv",
        status=TaskStatus.running,
        started_at=utc_now(),
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    frequency = payload.frequency.strip().lower()
    try:
        result = import_csv_bars(
            session,
            instrument_id=payload.instrument_id,
            frequency=frequency,
            source=task.source,
            csv_text=payload.csv_text,
        )
    except ValueError as exc:
        task.status = TaskStatus.failed
        task.finished_at = utc_now()
        task.message = json.dumps({"message": str(exc), "rows_imported": 0, "rows_updated": 0})
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
    task.message = json.dumps(
        {
            "message": "CSV import succeeded",
            "rows_imported": result.rows_imported,
            "rows_updated": result.rows_updated,
        }
    )
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

    import json

    frequency = payload.frequency.strip().lower()
    task = DataImportTask(
        source="akshare",
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
            instrument_id=payload.instrument_id,
            frequency=frequency,
            start_date=payload.start_date.strip(),
            end_date=payload.end_date.strip(),
            adjust=payload.adjust.strip(),
        )
    except (RuntimeError, ValueError) as exc:
        task.status = TaskStatus.failed
        task.finished_at = utc_now()
        task.message = json.dumps({"message": str(exc), "rows_imported": 0, "rows_updated": 0})
        session.add(task)
        session.commit()
        record_operation(
            session,
            action="market_data.fetch_public.failed",
            actor=current_user.username,
            target_type="instrument",
            target_id=str(payload.instrument_id),
            detail={"frequency": frequency, "message": str(exc), "source": "akshare"},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    task.status = TaskStatus.succeeded
    task.finished_at = utc_now()
    task.message = json.dumps(
        {
            "message": "Public data fetch succeeded",
            "rows_imported": result.rows_imported,
            "rows_updated": result.rows_updated,
        }
    )
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
            "source": "akshare",
        },
    )
    return task_response(task)


@router.get("/bars", response_model=list[BarResponse])
def list_bars(
    session: SessionDep,
    instrument_id: int = Query(gt=0),
    frequency: str = Query(min_length=1),
    limit: int = Query(default=200, gt=0, le=1000),
    current_user: User = Depends(get_current_user),
) -> list[BarResponse]:
    statement = (
        select(Bar)
        .where(Bar.instrument_id == instrument_id, Bar.frequency == frequency.strip().lower())
        .order_by(Bar.timestamp.desc())
        .limit(limit)
    )
    bars = list(reversed(session.exec(statement).all()))
    return [bar_response(bar) for bar in bars]


@router.get("/import-tasks", response_model=list[DataImportTaskResponse])
def list_import_tasks(
    session: SessionDep,
    limit: int = Query(default=20, gt=0, le=100),
    current_user: User = Depends(get_current_user),
) -> list[DataImportTaskResponse]:
    statement = select(DataImportTask).order_by(DataImportTask.created_at.desc()).limit(limit)
    return [task_response(task) for task in session.exec(statement).all()]
