from datetime import datetime, timedelta

from pytest import approx

from app.models import Bar
from app.services.indicators import (
    bollinger_band_values,
    build_technical_indicators,
    exponential_moving_average_values,
    latest_indicator_summary,
    macd_values,
    moving_average_at,
    moving_average_points,
    relative_strength_index_values,
)


def make_bars(closes: list[float]) -> list[Bar]:
    start = datetime(2026, 1, 1)
    return [
        Bar(
            instrument_id=1,
            frequency="1d",
            timestamp=start + timedelta(days=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1000 + index,
        )
        for index, close in enumerate(closes)
    ]


def values(series: list[dict]) -> list[float | None]:
    return [point["value"] for point in series]


def test_moving_average_points_are_aligned_to_input_bars() -> None:
    bars = make_bars([1, 2, 3, 4, 5])

    series = moving_average_points(bars, period=3)

    assert [point["timestamp"] for point in series] == [bar.timestamp.isoformat() for bar in bars]
    assert values(series) == [None, None, 2.0, 3.0, 4.0]
    assert moving_average_at(bars, index=4, period=3) == approx(4.0)


def test_exponential_moving_average_starts_from_first_close() -> None:
    series = exponential_moving_average_values([10, 12, 14], period=2)

    assert series == approx([10, 11.333333, 13.111111])


def test_macd_returns_dif_dea_and_hist_series() -> None:
    series = macd_values([10, 10, 10, 10])

    assert set(series) == {"dif", "dea", "hist"}
    assert series["dif"] == approx([0, 0, 0, 0])
    assert series["dea"] == approx([0, 0, 0, 0])
    assert series["hist"] == approx([0, 0, 0, 0])


def test_relative_strength_index_handles_trend_and_flat_series() -> None:
    rising = relative_strength_index_values([1, 2, 3, 4, 5, 6], period=3)
    flat = relative_strength_index_values([5, 5, 5, 5, 5], period=3)

    assert rising == [None, None, None, 100.0, 100.0, 100.0]
    assert flat == [None, None, None, 50.0, 50.0]


def test_bollinger_bands_use_population_standard_deviation() -> None:
    bands = bollinger_band_values([1, 2, 3], period=3, width=2)

    assert bands["mid"] == [None, None, 2.0]
    assert bands["upper"][2] == approx(3.632993, rel=1e-6)
    assert bands["lower"][2] == approx(0.367007, rel=1e-6)


def test_build_technical_indicators_and_latest_summary() -> None:
    bars = make_bars([1, 2, 3, 4, 5, 6])

    indicators = build_technical_indicators(bars)
    summary = latest_indicator_summary(indicators)

    assert values(indicators["ma"]["ma5"]) == [None, None, None, None, 3.0, 4.0]
    assert len(indicators["macd"]["hist"]) == len(bars)
    assert summary["ma"]["ma5"] == 4.0
    assert "macd" in summary
