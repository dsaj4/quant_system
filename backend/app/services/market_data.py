from dataclasses import dataclass
from datetime import datetime, time
import csv
from io import StringIO
from typing import Any, Callable

from sqlmodel import Session, select

from app.core.config import get_settings
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


PUBLIC_BAR_PROVIDERS: dict[str, PublicBarProvider] = {}


def register_public_bar_provider(name: str, provider: PublicBarProvider) -> None:
    normalized_name = name.strip().lower()
    if not normalized_name:
        raise ValueError("Provider name is required")
    PUBLIC_BAR_PROVIDERS[normalized_name] = provider


def get_public_bar_provider(name: str) -> PublicBarProvider:
    normalized_name = name.strip().lower()
    try:
        return PUBLIC_BAR_PROVIDERS[normalized_name]
    except KeyError as exc:
        raise ValueError(f"Unknown public data provider: {name}") from exc


def list_public_bar_providers() -> list[str]:
    return sorted(PUBLIC_BAR_PROVIDERS)


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
    adjust: str = "",
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
            Bar.adjust == adjust,
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
                    adjust=adjust,
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
    adjust: str = "",
) -> ImportResult:
    return upsert_bars(
        session,
        instrument_id=instrument_id,
        frequency=frequency,
        adjust=adjust,
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


def to_tushare_ts_code(symbol: str, exchange: str = "") -> str:
    clean_symbol = symbol.strip().upper()
    if "." in clean_symbol:
        return clean_symbol

    exchange_aliases = {
        "SH": "SH",
        "SSE": "SH",
        "XSHG": "SH",
        "SZ": "SZ",
        "SZSE": "SZ",
        "XSHE": "SZ",
        "BJ": "BJ",
        "BSE": "BJ",
    }
    normalized_exchange = exchange_aliases.get(exchange.strip().upper())
    if not normalized_exchange:
        raise ValueError("Tushare provider requires instrument exchange: SH, SZ, or BJ")
    return f"{clean_symbol}.{normalized_exchange}"


def tushare_frequency(frequency: str) -> str:
    normalized_frequency = frequency.strip().lower()
    frequency_map = {
        "1d": "D",
        "daily": "D",
        "day": "D",
        "d": "D",
        "1m": "1min",
        "1min": "1min",
        "5m": "5min",
        "5min": "5min",
        "15m": "15min",
        "15min": "15min",
        "30m": "30min",
        "30min": "30min",
        "60m": "60min",
        "60min": "60min",
    }
    try:
        return frequency_map[normalized_frequency]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare frequency: {frequency}") from exc


def _parse_date_input(value: str, *, end_of_day: bool = False) -> datetime:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Date value is required")
    if len(stripped) == 8 and stripped.isdigit():
        return datetime.strptime(stripped, "%Y%m%d")
    parsed = datetime.fromisoformat(stripped.replace("T", " "))
    if len(stripped) == 10 and end_of_day:
        return datetime.combine(parsed.date(), time(23, 59, 59))
    return parsed


def tushare_date(value: str, *, frequency: str, end_of_day: bool = False) -> str:
    parsed = _parse_date_input(value, end_of_day=end_of_day)
    if tushare_frequency(frequency) == "D":
        return parsed.strftime("%Y%m%d")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def normalize_tushare_row(row: dict[str, Any], line_number: int) -> ParsedBar:
    raw_timestamp = row.get("trade_time") or row.get("trade_date") or row.get("timestamp")
    try:
        timestamp_text = str(raw_timestamp).strip()
        if len(timestamp_text) == 8 and timestamp_text.isdigit():
            timestamp = datetime.strptime(timestamp_text, "%Y%m%d")
        else:
            timestamp = datetime.fromisoformat(timestamp_text.replace("T", " "))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Tushare timestamp on row {line_number}") from exc

    try:
        return ParsedBar(
            timestamp=timestamp,
            open=float(row.get("open")),
            high=float(row.get("high")),
            low=float(row.get("low")),
            close=float(row.get("close")),
            volume=float(row.get("vol") or row.get("volume") or row.get("amount") or 0),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Tushare numeric value on row {line_number}") from exc


def default_akshare_provider(
    *,
    symbol: str,
    exchange: str = "",
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


def default_tushare_provider(
    *,
    symbol: str,
    exchange: str = "",
    frequency: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> Any:
    settings = get_settings()
    if not settings.tushare_token:
        raise RuntimeError("Tushare token is not configured; set QUANT_TUSHARE_TOKEN")
    try:
        import tushare as ts  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("tushare is not installed; install tushare or choose another provider") from exc

    ts.set_token(settings.tushare_token)
    ts_code = to_tushare_ts_code(symbol, exchange)
    freq = tushare_frequency(frequency)
    adj = adjust.strip() or None
    return ts.pro_bar(
        ts_code=ts_code,
        freq=freq,
        start_date=tushare_date(start_date, frequency=frequency),
        end_date=tushare_date(end_date, frequency=frequency, end_of_day=True),
        adj=adj,
    )


def normalize_provider_row(provider_name: str, row: dict[str, Any], line_number: int) -> ParsedBar:
    if provider_name == "tushare":
        return normalize_tushare_row(row, line_number)
    return normalize_akshare_row(row, line_number)


def fetch_public_bars(
    session: Session,
    *,
    instrument_symbol: str,
    instrument_exchange: str = "",
    instrument_id: int,
    frequency: str,
    start_date: str,
    end_date: str,
    adjust: str = "",
    provider_name: str = "akshare",
    provider: PublicBarProvider | None = None,
) -> ImportResult:
    normalized_provider_name = provider_name.strip().lower() or "akshare"
    selected_provider = provider or get_public_bar_provider(normalized_provider_name)
    rows = rows_from_provider_result(
        selected_provider(
            symbol=instrument_symbol,
            exchange=instrument_exchange,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    )
    rows.sort(key=lambda row: str(row.get("trade_time") or row.get("trade_date") or row.get("timestamp") or ""))
    parsed_bars = [normalize_provider_row(normalized_provider_name, row, index) for index, row in enumerate(rows, start=1)]
    if not parsed_bars:
        raise ValueError("Public data provider returned no bars")

    return upsert_bars(
        session,
        instrument_id=instrument_id,
        frequency=frequency,
        adjust=adjust,
        source=normalized_provider_name,
        parsed_bars=parsed_bars,
        data_version=f"{normalized_provider_name}:{start_date}:{end_date}:{adjust}",
    )


register_public_bar_provider("akshare", default_akshare_provider)
register_public_bar_provider("tushare", default_tushare_provider)
