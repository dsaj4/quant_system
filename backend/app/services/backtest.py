from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import pstdev
from typing import Any

from app.models import Bar, StrategyParameterSet
from app.services.indicators import build_technical_indicators, latest_indicator_summary, moving_average_at


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


def _percent_parameter(parameters: dict, name: str, default: float) -> float:
    value = parameters.get(name, default)
    if not isinstance(value, int | float):
        return default
    return max(0.0, min(float(value), 100.0)) / 100


def _rate_parameter(parameters: dict, name: str, default: float = 0.0) -> float:
    value = parameters.get(name, default)
    if not isinstance(value, int | float):
        return default
    return max(0.0, float(value))


def _ma_filter_payload(*, side: str, bars: list[Bar], index: int, window: int) -> dict[str, Any]:
    moving_average = moving_average_at(bars, index, window)
    payload = {
        "enabled": True,
        "window": window,
        "value": round(moving_average, 6) if moving_average is not None else None,
        "passed": True,
        "rule": "ma_filter",
    }
    if moving_average is None:
        payload["rule"] = "insufficient_history_allows_trade"
        return payload

    close = bars[index].close
    if side == "sell":
        payload["passed"] = close >= moving_average
        payload["rule"] = "sell_only_when_close_above_ma"
        return payload
    if side == "buy":
        payload["passed"] = close <= moving_average
        payload["rule"] = "buy_only_when_close_below_ma"
        return payload
    return payload


def _disabled_ma_filter_payload(window: int) -> dict[str, Any]:
    return {
        "enabled": False,
        "window": window,
        "value": None,
        "passed": True,
        "rule": "disabled",
    }


def _grid_signal_reason(*, side: str, change_percent: float, reference_close: float, grid_percent: float) -> str:
    direction = "above" if side == "sell" else "below"
    return (
        f"Price moved {abs(change_percent):.4f}% {direction} reference "
        f"{reference_close:.6f}; grid threshold is {grid_percent:.4f}%."
    )


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

    parameters = parameter_set.parameters
    grid_percent = float(parameters.get("grid_percent", 1.5))
    base_position_percent = _percent_parameter(parameters, "base_position_percent", 50)
    trade_position_percent = _percent_parameter(parameters, "trade_position_percent", 10)
    fee_rate = _rate_parameter(parameters, "fee_rate")
    slippage_bps = _rate_parameter(parameters, "slippage_bps")
    slippage_rate = slippage_bps / 10000
    enable_ma_filter = bool(parameters.get("enable_ma_filter", False))
    ma_window = max(1, int(parameters.get("ma_window", 20) or 20))

    cash = float(initial_cash)
    position_qty = 0.0
    initial_budget = cash * base_position_percent
    if initial_budget > 0:
        execution_price = first_close * (1 + slippage_rate)
        quantity = initial_budget / (execution_price * (1 + fee_rate)) if execution_price > 0 else 0
        gross_amount = quantity * execution_price
        fee = gross_amount * fee_rate
        cash -= gross_amount + fee
        position_qty += quantity

    peak_equity = cash + position_qty * first_close
    equity_curve = []
    benchmark_curve = []
    drawdown_curve = []
    position_curve = []
    candles = []
    trade_markers = []
    trades = []
    signal_events = []

    reference_close = first_close

    for index, bar in enumerate(bars):
        if bar.close <= 0:
            raise ValueError("Close price must be positive")

        timestamp = bar.timestamp.isoformat()

        if index > 0:
            change_percent = ((bar.close - reference_close) / reference_close) * 100
            side = "sell" if change_percent > 0 else "buy"
            crosses_grid = abs(change_percent) >= grid_percent
            should_trade = crosses_grid
            ma_filter = _disabled_ma_filter_payload(ma_window)
            signal_event = None
            if crosses_grid:
                if enable_ma_filter:
                    ma_filter = _ma_filter_payload(side=side, bars=bars, index=index, window=ma_window)
                    should_trade = bool(ma_filter["passed"])
                signal_event = {
                    "timestamp": timestamp,
                    "side": side,
                    "price": bar.close,
                    "reference_price": round(reference_close, 6),
                    "change_percent": round(change_percent, 4),
                    "threshold_percent": round(grid_percent, 4),
                    "reason": "grid_threshold",
                    "reason_detail": _grid_signal_reason(
                        side=side,
                        change_percent=change_percent,
                        reference_close=reference_close,
                        grid_percent=grid_percent,
                    ),
                    "ma_filter": ma_filter,
                    "decision": "pending",
                }
                if not should_trade:
                    signal_event["decision"] = "blocked_by_ma_filter"
                    signal_events.append(signal_event)

            if should_trade:
                pre_trade_equity = cash + position_qty * bar.close
                target_notional = pre_trade_equity * trade_position_percent
                execution_price = bar.close * (1 - slippage_rate if side == "sell" else 1 + slippage_rate)
                quantity = 0.0
                gross_amount = 0.0
                fee = 0.0
                slippage = 0.0

                if side == "sell" and execution_price > 0 and position_qty > 0:
                    quantity = min(position_qty, target_notional / execution_price)
                    gross_amount = quantity * execution_price
                    fee = gross_amount * fee_rate
                    slippage = quantity * max(bar.close - execution_price, 0)
                    cash += gross_amount - fee
                    position_qty -= quantity
                elif side == "buy" and execution_price > 0 and cash > 0:
                    cash_budget = min(target_notional, cash)
                    quantity = cash_budget / (execution_price * (1 + fee_rate))
                    gross_amount = quantity * execution_price
                    fee = gross_amount * fee_rate
                    slippage = quantity * max(execution_price - bar.close, 0)
                    cash -= gross_amount + fee
                    position_qty += quantity

                if quantity > 0:
                    equity_after = cash + position_qty * bar.close
                    position_after = (position_qty * bar.close / equity_after * 100) if equity_after > 0 else 0
                    marker = {
                        "timestamp": timestamp,
                        "side": side,
                        "price": bar.close,
                        "reason": signal_event["reason"] if signal_event else "grid_threshold",
                    }
                    trade = {
                        "timestamp": timestamp,
                        "side": side,
                        "price": bar.close,
                        "execution_price": round(execution_price, 6),
                        "quantity": round(quantity, 6),
                        "amount": round(gross_amount, 6),
                        "fee": round(fee, 6),
                        "slippage": round(slippage, 6),
                        "cash_after": round(cash, 6),
                        "equity_after": round(equity_after, 6),
                        "position_after": round(position_after, 6),
                        "change_percent": round(change_percent, 4),
                        "reason": "grid_threshold",
                        "reason_detail": signal_event["reason_detail"] if signal_event else "Grid threshold reached.",
                        "reference_price": round(reference_close, 6),
                        "threshold_percent": round(grid_percent, 4),
                        "ma_filter": ma_filter,
                    }
                    trade_markers.append(marker)
                    trades.append(trade)
                    if signal_event:
                        signal_event.update(
                            {
                                "decision": "executed",
                                "execution_price": round(execution_price, 6),
                                "quantity": round(quantity, 6),
                                "fee": round(fee, 6),
                                "slippage": round(slippage, 6),
                            }
                        )
                        signal_events.append(signal_event)
                    reference_close = bar.close
                elif signal_event:
                    signal_event["decision"] = "skipped_no_available_cash_or_position"
                    signal_events.append(signal_event)

        equity = round(cash + position_qty * bar.close, 2)
        benchmark_value = round(initial_cash * (bar.close / first_close), 2)
        peak_equity = max(peak_equity, equity)
        drawdown = round((equity - peak_equity) / peak_equity, 6) if peak_equity else 0
        position_value = position_qty * bar.close
        position_percent = round(position_value / equity * 100, 6) if equity > 0 else 0

        equity_curve.append({"timestamp": timestamp, "value": equity})
        benchmark_curve.append({"timestamp": timestamp, "value": benchmark_value})
        drawdown_curve.append({"timestamp": timestamp, "value": drawdown})
        position_curve.append({"timestamp": timestamp, "value": position_percent})
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

    final_equity = equity_curve[-1]["value"] if equity_curve else initial_cash
    cumulative_return = round((final_equity / initial_cash) - 1, 6) if initial_cash else 0
    max_drawdown = min((point["value"] for point in drawdown_curve), default=0)
    win_rate = 0
    if trades:
        wins = [trade for trade in trades if trade["change_percent"] > 0]
        win_rate = round(len(wins) / len(trades), 6)

    performance_metrics = calculate_performance_metrics(
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        trades=trades,
    )
    technical_indicators = build_technical_indicators(bars)
    latest_trade = trades[-1] if trades else None
    latest_signal_event = signal_events[-1] if signal_events else None

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
        "parameters": parameters,
        "equity_curve": equity_curve,
        "benchmark_curve": benchmark_curve,
        "drawdown_curve": drawdown_curve,
        "candles": candles,
        "trade_markers": trade_markers,
        "position_curve": position_curve,
        "trade_table": trades,
        "orders": trades,
        "technical_indicators": technical_indicators,
        "indicator_summary": latest_indicator_summary(technical_indicators),
        "signal_events": signal_events,
        "signal_summary": {
            "strategy_id": parameter_set.strategy_id,
            "latest_signal": latest_trade["side"] if latest_trade else "hold",
            "latest_decision": latest_signal_event["decision"] if latest_signal_event else "hold",
            "latest_reason": (
                latest_signal_event["reason_detail"] if latest_signal_event else "No grid threshold signal generated."
            ),
            "signal_count": len(signal_events),
            "executed_signal_count": len(trades),
            "blocked_signal_count": len(
                [event for event in signal_events if event.get("decision") == "blocked_by_ma_filter"]
            ),
            "grid_percent": grid_percent,
            "ma_filter_enabled": enable_ma_filter,
            "ma_window": ma_window,
        },
        "execution_assumptions": {
            "initial_cash": initial_cash,
            "base_position_percent": round(base_position_percent * 100, 6),
            "trade_position_percent": round(trade_position_percent * 100, 6),
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "fees_included": fee_rate > 0,
            "slippage_included": slippage_bps > 0,
        },
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
