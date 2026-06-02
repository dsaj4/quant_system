from app.models import Bar, StrategyParameterSet
from app.services.backtest import BacktestResult, run_single_instrument_backtest


def run_single_instrument_paper_simulation(
    *,
    bars: list[Bar],
    parameter_set: StrategyParameterSet,
    initial_cash: float,
) -> BacktestResult:
    result = run_single_instrument_backtest(
        bars=bars,
        parameter_set=parameter_set,
        initial_cash=initial_cash,
    )
    latest_equity = result.result_payload["equity_curve"][-1]["value"]
    latest_position = result.result_payload["position_curve"][-1]["value"]
    latest_trade = result.result_payload["trade_table"][-1] if result.result_payload["trade_table"] else None
    signal_summary = result.result_payload.get("signal_summary") or {}
    signal_events = result.result_payload.get("signal_events") or []
    latest_signal_event = signal_events[-1] if signal_events else None
    paper_trades = result.result_payload.get("orders") or result.result_payload.get("trade_table") or []

    result.metrics.update(
        {
            "latest_equity": latest_equity,
            "latest_position_percent": latest_position,
            "latest_signal": latest_trade["side"] if latest_trade else "hold",
            "latest_decision": signal_summary.get("latest_decision", "hold"),
            "signal_count": signal_summary.get("signal_count", len(signal_events)),
            "simulated_trade_count": len(paper_trades),
            "blocked_signal_count": signal_summary.get("blocked_signal_count", 0),
        }
    )
    result.result_payload["paper_summary"] = {
        "latest_equity": latest_equity,
        "latest_position_percent": latest_position,
        "latest_signal": latest_trade["side"] if latest_trade else "hold",
        "latest_decision": signal_summary.get("latest_decision", "hold"),
        "latest_reason": signal_summary.get("latest_reason"),
        "signal_count": signal_summary.get("signal_count", len(signal_events)),
        "simulated_trade_count": len(paper_trades),
        "blocked_signal_count": signal_summary.get("blocked_signal_count", 0),
        "latest_trade": latest_trade,
        "latest_signal_event": latest_signal_event,
    }
    result.result_payload["paper_signals"] = signal_events
    result.result_payload["paper_trades"] = paper_trades
    return result
