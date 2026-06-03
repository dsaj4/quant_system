from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SnapshotStatus(str, Enum):
    draft = "draft"
    published = "published"
    revoked = "revoked"


class NarrativeStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    degraded = "degraded"
    failed = "failed"
    reviewed = "reviewed"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class Instrument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    exchange: str = Field(index=True)
    name: str
    asset_type: str = "stock"
    created_at: datetime = Field(default_factory=utc_now)


class DataSourceProvider(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    display_name: str
    role: str = Field(default="fallback", index=True)
    priority: int = Field(default=100, index=True)
    is_enabled: bool = Field(default=True, index=True)
    is_configured: bool = Field(default=False, index=True)
    credential_env_var: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Portfolio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class PortfolioInstrument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolio.id", index=True)
    instrument_id: int = Field(foreign_key="instrument.id", index=True)
    weight: float = 1.0


class Bar(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("instrument_id", "frequency", "timestamp", "adjust", name="uq_bar_identity"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    instrument_id: int = Field(foreign_key="instrument.id", index=True)
    frequency: str = Field(index=True)
    timestamp: datetime = Field(index=True)
    adjust: str = Field(default="", index=True)
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    source: str = "manual"
    data_version: str = ""


class DataImportTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    instrument_id: Optional[int] = Field(default=None, foreign_key="instrument.id", index=True)
    frequency: str = Field(default="", index=True)
    adjust: str = Field(default="", index=True)
    status: TaskStatus = Field(default=TaskStatus.pending, index=True)
    message: str = ""
    rows_imported: int = 0
    rows_updated: int = 0
    request_params: dict = Field(default_factory=dict, sa_column=Column(JSON))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class MarketDataSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    instrument_id: int = Field(foreign_key="instrument.id", index=True)
    provider: str = Field(default="tushare", index=True)
    frequency: str = Field(default="5m", index=True)
    start_date: str
    end_date: str
    adjust: str = ""
    interval_minutes: int = 60
    is_active: bool = Field(default=True, index=True)
    last_run_at: Optional[datetime] = None
    last_status: Optional[TaskStatus] = None
    last_message: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class StrategyParameterSet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: str = Field(index=True)
    name: str
    parameters: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)


class BacktestRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: str = Field(index=True)
    parameter_set_id: Optional[int] = Field(default=None, foreign_key="strategyparameterset.id")
    status: TaskStatus = Field(default=TaskStatus.pending, index=True)
    config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    result_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    message: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class NarrativeRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_run_id: int = Field(foreign_key="backtestrun.id", index=True)
    status: NarrativeStatus = Field(default=NarrativeStatus.pending, index=True)
    is_smoke_test: bool = Field(default=False, index=True)
    provider: str = Field(default="trading_agents", index=True)
    provider_model: str = ""
    analysis_date: str = Field(index=True)
    quant_rating: str = Field(default="neutral", index=True)
    quant_rating_inputs: dict = Field(default_factory=dict, sa_column=Column(JSON))
    target_scope: str = Field(default="instrument", index=True)
    target_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    ticker_mapping: dict = Field(default_factory=dict, sa_column=Column(JSON))
    coverage_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    input_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    provider_structured_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    provider_raw_suggestion: str = ""
    provider_conflict: bool = Field(default=False, index=True)
    degraded_reasons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    degraded_acknowledged_by: str = ""
    degraded_acknowledged_at: Optional[datetime] = None
    ai_draft_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    reviewed_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    reviewed_by: str = ""
    reviewed_at: Optional[datetime] = None
    review_note: str = ""
    error_message: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PaperRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: str = Field(index=True)
    status: TaskStatus = Field(default=TaskStatus.pending, index=True)
    config: dict = Field(default_factory=dict, sa_column=Column(JSON))
    latest_equity: float = 0
    message: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class PublishedSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_run_id: int = Field(foreign_key="backtestrun.id", index=True)
    version: int = 1
    status: SnapshotStatus = Field(default=SnapshotStatus.draft, index=True)
    title: str
    immutable_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class ShareLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_id: int = Field(foreign_key="publishedsnapshot.id", index=True)
    token_hash: str = Field(index=True)
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class OperationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str = Field(default="system", index=True)
    action: str = Field(index=True)
    target_type: str = ""
    target_id: str = ""
    detail: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
