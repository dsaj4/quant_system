from math import isfinite, sqrt
from typing import Any

from app.models import Bar


DEFAULT_MA_PERIODS = (5, 20, 60)
DEFAULT_EMA_PERIODS = (12, 26)


def _validate_period(period: int) -> int:
    if period <= 0:
        raise ValueError("Indicator period must be positive")
    return period


def _number(value: Any) -> float:
    number = float(value)
    if not isfinite(number):
        raise ValueError("Indicator input must be finite")
    return number


def _round_indicator(value: float | None, digits: int = 6) -> float | None:
    if value is None or not isfinite(value):
        return None
    return round(float(value), digits)


def _point(bar: Bar, value: float | None, digits: int = 6) -> dict[str, str | float | None]:
    return {
        "timestamp": bar.timestamp.isoformat(),
        "value": _round_indicator(value, digits),
    }


def _points_from_values(bars: list[Bar], values: list[float | None], digits: int = 6) -> list[dict[str, Any]]:
    return [_point(bar, value, digits) for bar, value in zip(bars, values, strict=True)]


def close_values(bars: list[Bar]) -> list[float]:
    return [_number(bar.close) for bar in bars]


def moving_average_values(values: list[float], period: int) -> list[float | None]:
    period = _validate_period(period)
    averages: list[float | None] = []
    running_total = 0.0
    for index, value in enumerate(values):
        running_total += _number(value)
        if index >= period:
            running_total -= _number(values[index - period])
        averages.append(running_total / period if index + 1 >= period else None)
    return averages


def moving_average_points(bars: list[Bar], period: int) -> list[dict[str, Any]]:
    return _points_from_values(bars, moving_average_values(close_values(bars), period), digits=4)


def moving_average_at(bars: list[Bar], index: int, period: int) -> float | None:
    if index < 0 or index >= len(bars):
        return None
    return moving_average_values(close_values(bars[: index + 1]), period)[index]


def exponential_moving_average_values(values: list[float], period: int) -> list[float]:
    period = _validate_period(period)
    if not values:
        return []

    alpha = 2 / (period + 1)
    ema_values = [_number(values[0])]
    for value in values[1:]:
        ema_values.append(_number(value) * alpha + ema_values[-1] * (1 - alpha))
    return ema_values


def exponential_moving_average_points(bars: list[Bar], period: int) -> list[dict[str, Any]]:
    return _points_from_values(bars, exponential_moving_average_values(close_values(bars), period), digits=4)


def macd_values(
    values: list[float],
    short_period: int = 12,
    long_period: int = 26,
    signal_period: int = 9,
) -> dict[str, list[float]]:
    if short_period >= long_period:
        raise ValueError("MACD short period must be smaller than long period")

    short_ema = exponential_moving_average_values(values, short_period)
    long_ema = exponential_moving_average_values(values, long_period)
    dif = [short - long for short, long in zip(short_ema, long_ema, strict=True)]
    dea = exponential_moving_average_values(dif, signal_period)
    hist = [(dif_value - dea_value) * 2 for dif_value, dea_value in zip(dif, dea, strict=True)]
    return {"dif": dif, "dea": dea, "hist": hist}


def macd_points(bars: list[Bar]) -> dict[str, list[dict[str, Any]]]:
    values = macd_values(close_values(bars))
    return {key: _points_from_values(bars, series, digits=4) for key, series in values.items()}


def relative_strength_index_values(values: list[float], period: int = 14) -> list[float | None]:
    period = _validate_period(period)
    if len(values) <= period:
        return [None for _ in values]

    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values, values[1:], strict=False):
        change = _number(current) - _number(previous)
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    rsi_values: list[float | None] = [None for _ in values]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    def calculate_rsi(gain: float, loss: float) -> float:
        if loss == 0 and gain == 0:
            return 50.0
        if loss == 0:
            return 100.0
        relative_strength = gain / loss
        return 100 - (100 / (1 + relative_strength))

    rsi_values[period] = calculate_rsi(average_gain, average_loss)
    for index in range(period + 1, len(values)):
        gain = gains[index - 1]
        loss = losses[index - 1]
        average_gain = (average_gain * (period - 1) + gain) / period
        average_loss = (average_loss * (period - 1) + loss) / period
        rsi_values[index] = calculate_rsi(average_gain, average_loss)

    return rsi_values


def relative_strength_index_points(bars: list[Bar], period: int = 14) -> list[dict[str, Any]]:
    return _points_from_values(bars, relative_strength_index_values(close_values(bars), period), digits=4)


def bollinger_band_values(values: list[float], period: int = 20, width: float = 2.0) -> dict[str, list[float | None]]:
    period = _validate_period(period)
    mid = moving_average_values(values, period)
    upper: list[float | None] = []
    lower: list[float | None] = []
    for index, average in enumerate(mid):
        if average is None:
            upper.append(None)
            lower.append(None)
            continue
        window = [_number(value) for value in values[index + 1 - period : index + 1]]
        variance = sum((value - average) ** 2 for value in window) / period
        standard_deviation = sqrt(variance)
        upper.append(average + width * standard_deviation)
        lower.append(average - width * standard_deviation)
    return {"mid": mid, "upper": upper, "lower": lower}


def bollinger_band_points(bars: list[Bar], period: int = 20, width: float = 2.0) -> dict[str, list[dict[str, Any]]]:
    values = bollinger_band_values(close_values(bars), period=period, width=width)
    return {key: _points_from_values(bars, series, digits=4) for key, series in values.items()}


def build_technical_indicators(bars: list[Bar]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    return {
        "ma": {f"ma{period}": moving_average_points(bars, period) for period in DEFAULT_MA_PERIODS},
        "ema": {f"ema{period}": exponential_moving_average_points(bars, period) for period in DEFAULT_EMA_PERIODS},
        "macd": macd_points(bars),
        "rsi": {"rsi14": relative_strength_index_points(bars, 14)},
        "boll": bollinger_band_points(bars, period=20, width=2.0),
    }


def latest_indicator_summary(indicators: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for family, series_by_name in indicators.items():
        family_summary: dict[str, float] = {}
        for name, series in series_by_name.items():
            for point in reversed(series):
                value = point.get("value")
                if isinstance(value, int | float) and not isinstance(value, bool) and isfinite(float(value)):
                    family_summary[name] = float(value)
                    break
        if family_summary:
            summary[family] = family_summary
    return summary
