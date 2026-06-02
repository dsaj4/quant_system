from dataclasses import dataclass
from datetime import date, datetime

from app.models import Bar


FREQUENCY_INTERVAL_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "1h": 60,
    "1d": 1440,
    "d": 1440,
    "daily": 1440,
}


@dataclass(frozen=True)
class DataCompleteness:
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
    calendar_source: str | None = None
    expected_trading_days: int | None = None
    missing_trading_days: list[str] | None = None
    warnings: list[str] | None = None


def expected_interval_minutes(frequency: str) -> int | None:
    return FREQUENCY_INTERVAL_MINUTES.get(frequency.strip().lower())


def _normalize_trading_dates(values: list[str | date | datetime] | None) -> list[str] | None:
    if values is None:
        return None

    normalized = []
    for value in values:
        if isinstance(value, datetime):
            normalized.append(value.date().isoformat())
        elif isinstance(value, date):
            normalized.append(value.isoformat())
        else:
            text = str(value).strip()
            if len(text) == 8 and text.isdigit():
                normalized.append(datetime.strptime(text, "%Y%m%d").date().isoformat())
            else:
                normalized.append(datetime.fromisoformat(text).date().isoformat())
    return sorted(set(normalized))


def assess_bar_completeness(
    *,
    instrument_id: int,
    frequency: str,
    bars: list[Bar],
    expected_trading_dates: list[str | date | datetime] | None = None,
    calendar_source: str | None = None,
    minimum_bar_count: int = 30,
) -> DataCompleteness:
    normalized_frequency = frequency.strip().lower()
    interval_minutes = expected_interval_minutes(normalized_frequency)
    normalized_trading_dates = _normalize_trading_dates(expected_trading_dates)

    if not bars:
        return DataCompleteness(
            instrument_id=instrument_id,
            frequency=normalized_frequency,
            bar_count=0,
            first_timestamp=None,
            last_timestamp=None,
            expected_interval_minutes=interval_minutes,
            expected_bar_count=None,
            missing_bar_count=None,
            completeness_ratio=None,
            gap_count=0,
            largest_gap_minutes=None,
            status="empty",
            message="No bars found for selected instrument and frequency.",
            calendar_source=calendar_source,
            expected_trading_days=len(normalized_trading_dates) if normalized_trading_dates is not None else None,
            missing_trading_days=normalized_trading_dates,
            warnings=["No bars found for selected instrument and frequency."],
        )

    sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
    first_timestamp = sorted_bars[0].timestamp
    last_timestamp = sorted_bars[-1].timestamp
    largest_gap_minutes: float | None = None
    gap_count = 0
    missing_bar_count: int | None = None
    expected_bar_count: int | None = None
    completeness_ratio: float | None = None
    missing_trading_days: list[str] | None = None
    expected_trading_days: int | None = None
    warnings: list[str] = []

    if normalized_frequency in {"1d", "d", "daily", "day"} and normalized_trading_dates is not None:
        actual_dates = {bar.timestamp.date().isoformat() for bar in sorted_bars}
        missing_trading_days = [value for value in normalized_trading_dates if value not in actual_dates]
        expected_trading_days = len(normalized_trading_dates)
        expected_bar_count = expected_trading_days
        missing_bar_count = len(missing_trading_days)
        completeness_ratio = round(len(actual_dates & set(normalized_trading_dates)) / expected_trading_days, 6) if expected_trading_days else None
        gap_count = 1 if missing_trading_days else 0
        if missing_trading_days:
            warnings.append(f"Missing {len(missing_trading_days)} expected trading day(s).")
    elif interval_minutes:
        missing_bar_count = 0
        for previous, current in zip(sorted_bars, sorted_bars[1:], strict=False):
            gap_minutes = (current.timestamp - previous.timestamp).total_seconds() / 60
            largest_gap_minutes = max(largest_gap_minutes or gap_minutes, gap_minutes)
            missing_in_gap = max(round(gap_minutes / interval_minutes) - 1, 0)
            if missing_in_gap > 0:
                gap_count += 1
                missing_bar_count += missing_in_gap

        expected_bar_count = len(sorted_bars) + missing_bar_count
        completeness_ratio = round(len(sorted_bars) / expected_bar_count, 6) if expected_bar_count else None

    status = "ok"
    message = "Data continuity looks usable for the selected frequency."
    if interval_minutes is None:
        status = "unknown_frequency"
        message = "Frequency is not mapped to an expected interval; continuity gaps were not evaluated."
    elif missing_trading_days:
        status = "warning"
        message = f"Detected {len(missing_trading_days)} missing trading day(s) before running backtests."
    elif gap_count:
        status = "warning"
        message = f"Detected {gap_count} interval gap(s) before running backtests."
    if len(sorted_bars) < minimum_bar_count:
        warnings.append(f"Sample has fewer than {minimum_bar_count} bars; report interpretation should stay conservative.")
        if status == "ok":
            status = "warning"
            message = f"Sample has fewer than {minimum_bar_count} bars before running backtests."

    return DataCompleteness(
        instrument_id=instrument_id,
        frequency=normalized_frequency,
        bar_count=len(sorted_bars),
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        expected_interval_minutes=interval_minutes,
        expected_bar_count=expected_bar_count,
        missing_bar_count=missing_bar_count,
        completeness_ratio=completeness_ratio,
        gap_count=gap_count,
        largest_gap_minutes=round(largest_gap_minutes, 6) if largest_gap_minutes is not None else None,
        status=status,
        message=message,
        calendar_source=calendar_source,
        expected_trading_days=expected_trading_days,
        missing_trading_days=missing_trading_days or [],
        warnings=warnings,
    )
