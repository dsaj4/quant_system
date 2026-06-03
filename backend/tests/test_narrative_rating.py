from app.models import BacktestRun, TaskStatus
from app.services.narrative_rating import QuantRating, calculate_quant_rating


def make_backtest(metrics: dict, data_quality: dict | None = None) -> BacktestRun:
    return BacktestRun(
        strategy_id="rolling_t_grid",
        status=TaskStatus.succeeded,
        metrics=metrics,
        result_payload={"data_quality": data_quality or {"status": "ok", "warnings": []}},
    )


def test_negative_cumulative_return_is_cautious() -> None:
    result = calculate_quant_rating(
        make_backtest(
            {
                "cumulative_return": -0.01,
                "max_drawdown": -0.02,
                "sharpe_ratio": 1.2,
                "return_drawdown_ratio": 2.0,
                "bar_count": 60,
                "trade_count": 4,
            }
        )
    )

    assert result.rating == QuantRating.cautious
    assert result.inputs["cumulative_return"] == -0.01


def test_severe_drawdown_is_cautious() -> None:
    result = calculate_quant_rating(
        make_backtest(
            {
                "cumulative_return": 0.08,
                "max_drawdown": -0.26,
                "sharpe_ratio": 1.4,
                "return_drawdown_ratio": 0.31,
                "bar_count": 80,
                "trade_count": 6,
            }
        )
    )

    assert result.rating == QuantRating.cautious
    assert result.inputs["max_drawdown"] == -0.26


def test_data_quality_warning_caps_rating_at_neutral() -> None:
    result = calculate_quant_rating(
        make_backtest(
            {
                "cumulative_return": 0.18,
                "max_drawdown": -0.04,
                "sharpe_ratio": 2.2,
                "return_drawdown_ratio": 4.5,
                "bar_count": 12,
                "trade_count": 5,
            },
            data_quality={"status": "warning", "warnings": ["Sample has fewer than 30 bars."]},
        )
    )

    assert result.rating == QuantRating.neutral
    assert result.inputs["data_quality_status"] == "warning"
    assert result.inputs["rating_cap"] == "neutral"


def test_positive_return_acceptable_drawdown_and_sufficient_sample_is_positive() -> None:
    result = calculate_quant_rating(
        make_backtest(
            {
                "cumulative_return": 0.12,
                "max_drawdown": -0.06,
                "sharpe_ratio": 1.1,
                "return_drawdown_ratio": 2.0,
                "bar_count": 60,
                "trade_count": 4,
            }
        )
    )

    assert result.rating == QuantRating.positive


def test_weak_or_mixed_metrics_are_neutral() -> None:
    result = calculate_quant_rating(
        make_backtest(
            {
                "cumulative_return": 0.015,
                "max_drawdown": -0.08,
                "sharpe_ratio": 0.2,
                "return_drawdown_ratio": 0.1875,
                "bar_count": 60,
                "trade_count": 2,
            }
        )
    )

    assert result.rating == QuantRating.neutral
