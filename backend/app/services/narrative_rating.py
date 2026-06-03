from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.models import BacktestRun


class QuantRating(str, Enum):
    positive = "positive"
    neutral = "neutral"
    cautious = "cautious"


MIN_POSITIVE_RETURN = 0.05
MAX_ACCEPTABLE_DRAWDOWN = -0.12
SEVERE_DRAWDOWN = -0.25
MIN_POSITIVE_SHARPE = 0.8
MIN_RETURN_DRAWDOWN_RATIO = 1.0
MIN_SAMPLE_BARS = 30
MIN_POSITIVE_TRADES = 3


@dataclass(frozen=True)
class RatingResult:
    rating: QuantRating
    inputs: dict[str, Any]


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _integer(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def calculate_quant_rating(backtest: BacktestRun) -> RatingResult:
    metrics = backtest.metrics or {}
    data_quality = (backtest.result_payload or {}).get("data_quality") or {}
    warnings = data_quality.get("warnings") or []

    cumulative_return = _number(metrics.get("cumulative_return"))
    max_drawdown = _number(metrics.get("max_drawdown"))
    sharpe_ratio = _number(metrics.get("sharpe_ratio"))
    return_drawdown_ratio = _number(metrics.get("return_drawdown_ratio"))
    bar_count = _integer(metrics.get("bar_count"))
    trade_count = _integer(metrics.get("trade_count"))
    data_quality_status = str(data_quality.get("status") or "unknown")

    inputs: dict[str, Any] = {
        "cumulative_return": cumulative_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "return_drawdown_ratio": return_drawdown_ratio,
        "bar_count": bar_count,
        "trade_count": trade_count,
        "data_quality_status": data_quality_status,
        "data_quality_warning_count": len(warnings),
        "thresholds": {
            "min_positive_return": MIN_POSITIVE_RETURN,
            "max_acceptable_drawdown": MAX_ACCEPTABLE_DRAWDOWN,
            "severe_drawdown": SEVERE_DRAWDOWN,
            "min_positive_sharpe": MIN_POSITIVE_SHARPE,
            "min_return_drawdown_ratio": MIN_RETURN_DRAWDOWN_RATIO,
            "min_sample_bars": MIN_SAMPLE_BARS,
            "min_positive_trades": MIN_POSITIVE_TRADES,
        },
    }

    if cumulative_return < 0:
        inputs["primary_reason"] = "negative_cumulative_return"
        return RatingResult(rating=QuantRating.cautious, inputs=inputs)

    if max_drawdown <= SEVERE_DRAWDOWN:
        inputs["primary_reason"] = "severe_drawdown"
        return RatingResult(rating=QuantRating.cautious, inputs=inputs)

    data_quality_caps_rating = data_quality_status != "ok" or bool(warnings) or bar_count < MIN_SAMPLE_BARS
    if data_quality_caps_rating:
        inputs["rating_cap"] = "neutral"

    positive_candidate = (
        cumulative_return >= MIN_POSITIVE_RETURN
        and max_drawdown >= MAX_ACCEPTABLE_DRAWDOWN
        and sharpe_ratio >= MIN_POSITIVE_SHARPE
        and return_drawdown_ratio >= MIN_RETURN_DRAWDOWN_RATIO
        and bar_count >= MIN_SAMPLE_BARS
        and trade_count >= MIN_POSITIVE_TRADES
    )

    if positive_candidate and not data_quality_caps_rating:
        inputs["primary_reason"] = "positive_metrics"
        return RatingResult(rating=QuantRating.positive, inputs=inputs)

    inputs["primary_reason"] = "mixed_or_capped_metrics"
    return RatingResult(rating=QuantRating.neutral, inputs=inputs)
