from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import pstdev
from typing import Any

from app.models import Bar, StrategyParameterSet


@dataclass(frozen=True)
class BacktestResult:
    metrics: dict
    result_payload: dict


@dataclass(frozen=True)
class PortfolioLeg:
    instrument_id: int
    symbol: str
    weight: float
    bars: list[Bar]


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _point_value(point: dict[str, Any]) -> float | None:
    value = point.get("value")
    if isinstance(value, int | float):
        return float(value)
    return None


def _round_metric(value: float) -> float:
    if not isinstance(value, int | float):
        return 0
    return round(float(value), 6)


def calculate_performance_metrics(
    *,
    equity_curve: list[dict[str, Any]],
    drawdown_curve: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> dict:
    values = [_point_value(point) for point in equity_curve]
    values = [value for value in values if value is not None and value > 0]
    first_value = values[0] if values else 0
    last_value = values[-1] if values else 0
    cumulative_return = (last_value / first_value) - 1 if first_value > 0 and last_value > 0 and len(values) > 1 else 0

    first_timestamp = _parse_timestamp(equity_curve[0].get("timestamp")) if equity_curve else None
    last_timestamp = _parse_timestamp(equity_curve[-1].get("timestamp")) if equity_curve else None
    elapsed_days = 0.0
    if first_timestamp and last_timestamp and last_timestamp > first_timestamp:
        elapsed_days = (last_timestamp - first_timestamp).total_seconds() / 86400

    annualized_return = 0.0
    if elapsed_days >= 1 and first_value > 0 and last_value > 0 and len(values) > 1:
        annualized_return = (last_value / first_value) ** (365 / elapsed_days) - 1

    period_returns = [
        (current / previous) - 1
        for previous, current in zip(values, values[1:], strict=False)
        if previous > 0 and current > 0
    ]
    annualized_volatility = 0.0
    if len(period_returns) > 1 and elapsed_days >= 1:
        periods_per_year = len(period_returns) * 365 / elapsed_days
        annualized_volatility = pstdev(period_returns) * sqrt(periods_per_year)

    drawdowns = [
        float(point["value"])
        for point in drawdown_curve
        if isinstance(point, dict) and isinstance(point.get("value"), int | float)
    ]
    max_drawdown = min(drawdowns, default=0)
    drawdown_abs = abs(max_drawdown)

    trade_returns: list[float] = []
    for trade in trades:
        change_percent = trade.get("change_percent")
        pnl_percent = trade.get("pnl_percent")
        if isinstance(change_percent, int | float):
            trade_returns.append(float(change_percent) / 100)
        elif isinstance(pnl_percent, int | float):
            pnl_value = float(pnl_percent)
            trade_returns.append(pnl_value if abs(pnl_value) <= 1 else pnl_value / 100)

    wins = [value for value in trade_returns if value > 0]
    losses = [value for value in trade_returns if value < 0]
    average_win = sum(wins) / len(wins) if wins else 0
    average_loss = sum(losses) / len(losses) if losses else 0
    profit_loss_ratio = average_win / abs(average_loss) if average_win > 0 and average_loss < 0 else 0

    return {
        "annualized_return": _round_metric(annualized_return),
        "annualized_volatility": _round_metric(annualized_volatility),
        "sharpe_ratio": _round_metric(annualized_return / annualized_volatility if annualized_volatility else 0),
        "calmar_ratio": _round_metric(annualized_return / drawdown_abs if drawdown_abs else 0),
        "return_drawdown_ratio": _round_metric(cumulative_return / drawdown_abs if drawdown_abs else 0),
        "average_win": _round_metric(average_win),
        "average_loss": _round_metric(average_loss),
        "profit_loss_ratio": _round_metric(profit_loss_ratio),
    }


def run_single_instrument_backtest(
    *,
    bars: list[Bar],
    parameter_set: StrategyParameterSet,
    initial_cash: float,
) -> BacktestResult:
    if not bars:
        raise ValueError("No bars found for selected instrument and frequency")

    first_close = bars[0].close
    if first_close <= 0:
        raise ValueError("First close price must be positive")

    peak_equity = initial_cash
    equity_curve = []
    drawdown_curve = []
    position_curve = []
    candles = []
    trade_markers = []
    trades = []

    grid_percent = float(parameter_set.parameters.get("grid_percent", 1.5))
    reference_close = first_close

    for index, bar in enumerate(bars):
        equity = round(initial_cash * (bar.close / first_close), 2)
        peak_equity = max(peak_equity, equity)
        drawdown = round((equity - peak_equity) / peak_equity, 6) if peak_equity else 0

        timestamp = bar.timestamp.isoformat()
        equity_curve.append({"timestamp": timestamp, "value": equity})
        drawdown_curve.append({"timestamp": timestamp, "value": drawdown})
        position_curve.append({"timestamp": timestamp, "value": parameter_set.parameters.get("base_position_percent", 50)})
        candles.append(
            {
                "timestamp": timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
        )

        if index == 0:
            continue

        change_percent = ((bar.close - reference_close) / reference_close) * 100
        if abs(change_percent) >= grid_percent:
            side = "sell" if change_percent > 0 else "buy"
            marker = {"timestamp": timestamp, "side": side, "price": bar.close}
            trade_markers.append(marker)
            trades.append(
                {
                    "timestamp": timestamp,
                    "side": side,
                    "price": bar.close,
                    "change_percent": round(change_percent, 4),
                }
            )
            reference_close = bar.close

    cumulative_return = round((bars[-1].close / first_close) - 1, 6)
    max_drawdown = min((point["value"] for point in drawdown_curve), default=0)
    win_rate = 0
    if trades:
        wins = [trade for trade in trades if trade["side"] == "sell"]
        win_rate = round(len(wins) / len(trades), 6)

    performance_metrics = calculate_performance_metrics(
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        trades=trades,
    )

    metrics = {
        "bar_count": len(bars),
        "trade_count": len(trades),
        "cumulative_return": cumulative_return,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        **performance_metrics,
    }
    result_payload = {
        "strategy_id": parameter_set.strategy_id,
        "parameters": parameter_set.parameters,
        "equity_curve": equity_curve,
        "benchmark_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "candles": candles,
        "trade_markers": trade_markers,
        "position_curve": position_curve,
        "trade_table": trades,
        "risk_disclosure": "Backtest results are simulated and do not represent real-money trading.",
    }
    return BacktestResult(metrics=metrics, result_payload=result_payload)


def run_portfolio_backtest(
    *,
    legs: list[PortfolioLeg],
    parameter_set: StrategyParameterSet,
    initial_cash: float,
) -> BacktestResult:
    if not legs:
        raise ValueError("Portfolio has no positions")

    for leg in legs:
        if leg.weight <= 0:
            raise ValueError(f"Portfolio position weight must be positive: {leg.symbol}")
        if not leg.bars:
            raise ValueError(f"No bars found for portfolio instrument: {leg.symbol}")

    total_weight = sum(leg.weight for leg in legs)
    if total_weight <= 0:
        raise ValueError("Portfolio total weight must be positive")

    bar_maps = [{bar.timestamp: bar for bar in leg.bars} for leg in legs]
    common_timestamps = sorted(set.intersection(*(set(bar_map) for bar_map in bar_maps)))
    if not common_timestamps:
        raise ValueError("No overlapping bars found for selected portfolio and frequency")

    first_timestamp = common_timestamps[0]
    first_closes = []
    for leg, bar_map in zip(legs, bar_maps, strict=True):
        first_close = bar_map[first_timestamp].close
        if first_close <= 0:
            raise ValueError(f"First close price must be positive: {leg.symbol}")
        first_closes.append(first_close)

    synthetic_bars: list[Bar] = []
    for timestamp in common_timestamps:
        index_close = 0.0
        index_volume = 0.0
        for leg, bar_map, first_close in zip(legs, bar_maps, first_closes, strict=True):
            bar = bar_map[timestamp]
            normalized_weight = leg.weight / total_weight
            index_close += normalized_weight * (bar.close / first_close) * 100
            index_volume += bar.volume

        synthetic_bars.append(
            Bar(
                instrument_id=0,
                frequency=legs[0].bars[0].frequency,
                timestamp=timestamp,
                open=round(index_close, 6),
                high=round(index_close, 6),
                low=round(index_close, 6),
                close=round(index_close, 6),
                volume=index_volume,
                source="portfolio",
                data_version="synthetic",
            )
        )

    result = run_single_instrument_backtest(
        bars=synthetic_bars,
        parameter_set=parameter_set,
        initial_cash=initial_cash,
    )
    result.result_payload["scope"] = "portfolio"
    result.result_payload["portfolio_legs"] = [
        {
            "instrument_id": leg.instrument_id,
            "symbol": leg.symbol,
            "weight": leg.weight,
            "normalized_weight": round(leg.weight / total_weight, 6),
            "bar_count": len(leg.bars),
        }
        for leg in legs
    ]
    return result
