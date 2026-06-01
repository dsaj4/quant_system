from dataclasses import dataclass
from datetime import datetime
import csv
from io import StringIO
from typing import Any, Callable

from sqlmodel import Session, select

from app.models import Bar


REQUIRED_CSV_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


@dataclass(frozen=True)
class ParsedBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class ImportResult:
    rows_imported: int
    rows_updated: int


PublicBarProvider = Callable[..., Any]


def parse_csv_bars(csv_text: str) -> list[ParsedBar]:
    reader = csv.DictReader(StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise ValueError("CSV header is required")

    missing_columns = REQUIRED_CSV_COLUMNS - set(reader.fieldnames)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing CSV columns: {missing}")

    bars: list[ParsedBar] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            timestamp = datetime.fromisoformat(row["timestamp"].strip())
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp on line {line_number}") from exc

        try:
            bars.append(
                ParsedBar(
                    timestamp=timestamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value on line {line_number}") from exc

    if not bars:
        raise ValueError("CSV must contain at least one bar row")

    return bars


def upsert_bars(
    session: Session,
    *,
    instrument_id: int,
    frequency: str,
    source: str,
    parsed_bars: list[ParsedBar],
    data_version: str = "",
) -> ImportResult:
    rows_imported = 0
    rows_updated = 0

    for parsed in parsed_bars:
        statement = select(Bar).where(
            Bar.instrument_id == instrument_id,
            Bar.frequency == frequency,
            Bar.timestamp == parsed.timestamp,
        )
        existing_bar = session.exec(statement).first()
        if existing_bar:
            existing_bar.open = parsed.open
            existing_bar.high = parsed.high
            existing_bar.low = parsed.low
            existing_bar.close = parsed.close
            existing_bar.volume = parsed.volume
            existing_bar.source = source
            existing_bar.data_version = data_version
            rows_updated += 1
        else:
            session.add(
                Bar(
                    instrument_id=instrument_id,
                    frequency=frequency,
                    timestamp=parsed.timestamp,
                    open=parsed.open,
                    high=parsed.high,
                    low=parsed.low,
                    close=parsed.close,
                    volume=parsed.volume,
                    source=source,
                    data_version=data_version,
                )
            )
            rows_imported += 1

    session.commit()
    return ImportResult(rows_imported=rows_imported, rows_updated=rows_updated)


def import_csv_bars(
    session: Session,
    *,
    instrument_id: int,
    frequency: str,
    source: str,
    csv_text: str,
) -> ImportResult:
    return upsert_bars(
        session,
        instrument_id=instrument_id,
        frequency=frequency,
        source=source,
        parsed_bars=parse_csv_bars(csv_text),
    )


def normalize_akshare_row(row: dict[str, Any], line_number: int) -> ParsedBar:
    try:
        timestamp = datetime.fromisoformat(str(row.get("时间") or row.get("日期") or row.get("timestamp")).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid public data timestamp on row {line_number}") from exc

    try:
        return ParsedBar(
            timestamp=timestamp,
            open=float(row.get("开盘")),
            high=float(row.get("最高")),
            low=float(row.get("最低")),
            close=float(row.get("收盘")),
            volume=float(row.get("成交量")),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid public data numeric value on row {line_number}") from exc


def rows_from_provider_result(provider_result: Any) -> list[dict[str, Any]]:
    if hasattr(provider_result, "to_dict"):
        return list(provider_result.to_dict(orient="records"))
    return list(provider_result)


def default_akshare_provider(
    *,
    symbol: str,
    frequency: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> Any:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("akshare is not installed; use CSV import or install akshare for public data fetch") from exc

    clean_symbol = symbol.split(".")[0]
    if frequency in {"1d", "daily", "day"}:
        return ak.stock_zh_a_hist(
            symbol=clean_symbol,
            period="daily",
            start_date=start_date.replace("-", "")[:8],
            end_date=end_date.replace("-", "")[:8],
            adjust=adjust,
        )

    minute_period = frequency.rstrip("m")
    if minute_period not in {"1", "5", "15", "30", "60"}:
        raise ValueError(f"Unsupported public data frequency: {frequency}")

    return ak.stock_zh_a_hist_min_em(
        symbol=clean_symbol,
        start_date=start_date,
        end_date=end_date,
        period=minute_period,
        adjust=adjust,
    )


def fetch_public_bars(
    session: Session,
    *,
    instrument_symbol: str,
    instrument_id: int,
    frequency: str,
    start_date: str,
    end_date: str,
    adjust: str = "",
    provider: PublicBarProvider = default_akshare_provider,
) -> ImportResult:
    rows = rows_from_provider_result(
        provider(
            symbol=instrument_symbol,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    )
    parsed_bars = [normalize_akshare_row(row, index) for index, row in enumerate(rows, start=1)]
    if not parsed_bars:
        raise ValueError("Public data provider returned no bars")

    return upsert_bars(
        session,
        instrument_id=instrument_id,
        frequency=frequency,
        source="akshare",
        parsed_bars=parsed_bars,
        data_version=f"akshare:{start_date}:{end_date}:{adjust}",
    )
