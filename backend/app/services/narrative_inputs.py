from datetime import date, datetime
from typing import Any

from sqlmodel import Session

from app.models import BacktestRun, Instrument, PortfolioInstrument


SUPPORTED_EXCHANGE_SUFFIXES = {
    "SH": ".SS",
    "SSE": ".SS",
    "SZ": ".SZ",
    "SZSE": ".SZ",
}


def _identity(instrument: Instrument) -> str:
    return f"{instrument.symbol}.{instrument.exchange}"


def map_instrument_to_tradingagents_ticker(instrument: Instrument) -> str:
    exchange = instrument.exchange.strip().upper()
    suffix = SUPPORTED_EXCHANGE_SUFFIXES.get(exchange)
    if not suffix:
        raise ValueError(f"Unsupported exchange for TradingAgents ticker mapping: {instrument.exchange}")
    return f"{instrument.symbol.strip()}{suffix}"


def _parse_timestamp_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _series_timestamps(result_payload: dict) -> list[str]:
    for key in ("equity_curve", "candles"):
        series = result_payload.get(key) or []
        timestamps = [point.get("timestamp") for point in series if isinstance(point, dict) and point.get("timestamp")]
        if timestamps:
            return timestamps
    return []


def extract_backtest_end_date(result_payload: dict) -> date | None:
    timestamps = _series_timestamps(result_payload or {})
    return _parse_timestamp_date(timestamps[-1]) if timestamps else None


def _extract_period(result_payload: dict) -> dict[str, str | None]:
    timestamps = _series_timestamps(result_payload or {})
    return {
        "start": timestamps[0] if timestamps else None,
        "end": timestamps[-1] if timestamps else None,
    }


def _require_instrument(session: Session, instrument_id: int | None) -> Instrument:
    if instrument_id is None:
        raise ValueError("Narrative input requires an instrument id")
    instrument = session.get(Instrument, instrument_id)
    if not instrument:
        raise ValueError(f"Unknown instrument id: {instrument_id}")
    return instrument


def _target_from_instrument(instrument: Instrument, weight: float | None = None) -> dict:
    target = {
        "instrument_id": instrument.id,
        "symbol": instrument.symbol,
        "exchange": instrument.exchange,
        "name": instrument.name,
        "asset_type": instrument.asset_type,
        "tradingagents_ticker": map_instrument_to_tradingagents_ticker(instrument),
    }
    if weight is not None:
        target["weight"] = weight
    return target


def _instrument_targets(session: Session, backtest: BacktestRun) -> tuple[list[dict], dict]:
    config = backtest.config or {}
    instrument = _require_instrument(session, config.get("instrument_id"))
    targets = [_target_from_instrument(instrument)]
    return targets, {
        "covered_count": 1,
        "total_position_count": 1,
        "coverage_limit": None,
    }


def _portfolio_targets(session: Session, backtest: BacktestRun) -> tuple[list[dict], dict]:
    config = backtest.config or {}
    positions = config.get("positions") or []
    if positions:
        sorted_positions = sorted(positions, key=lambda item: float(item.get("weight") or 0), reverse=True)
        total_position_count = len(sorted_positions)
        selected_positions = sorted_positions[:3]
        targets = [
            _target_from_instrument(
                _require_instrument(session, int(position.get("instrument_id"))),
                weight=float(position.get("weight") or 0),
            )
            for position in selected_positions
        ]
        return targets, {
            "covered_count": len(targets),
            "total_position_count": total_position_count,
            "coverage_limit": 3,
        }

    portfolio_id = config.get("portfolio_id")
    rows = session.query(PortfolioInstrument).filter(PortfolioInstrument.portfolio_id == portfolio_id).all()
    sorted_rows = sorted(rows, key=lambda row: row.weight, reverse=True)
    targets = [
        _target_from_instrument(_require_instrument(session, row.instrument_id), weight=float(row.weight))
        for row in sorted_rows[:3]
    ]
    return targets, {
        "covered_count": len(targets),
        "total_position_count": len(sorted_rows),
        "coverage_limit": 3,
    }


def _ticker_mapping(targets: list[dict]) -> dict[str, str]:
    return {
        f"{target['symbol']}.{target['exchange']}": target["tradingagents_ticker"]
        for target in targets
    }


def build_narrative_input_summary(
    session: Session,
    backtest: BacktestRun,
    analysis_date: date,
    *,
    today: date | None = None,
) -> dict:
    current_date = today or date.today()
    if analysis_date > current_date:
        raise ValueError("Analysis date cannot be later than current date")

    config = backtest.config or {}
    result_payload = backtest.result_payload or {}
    scope = config.get("scope") or ("portfolio" if config.get("portfolio_id") else "instrument")

    if scope == "portfolio":
        targets, coverage_summary = _portfolio_targets(session, backtest)
    else:
        targets, coverage_summary = _instrument_targets(session, backtest)

    warnings: list[str] = []
    backtest_end_date = extract_backtest_end_date(result_payload)
    if backtest_end_date and analysis_date < backtest_end_date:
        warnings.append("Analysis date is earlier than the backtest end date.")

    return {
        "backtest_id": backtest.id,
        "strategy_id": backtest.strategy_id,
        "parameter_set_id": backtest.parameter_set_id,
        "target_scope": scope,
        "target_label": config.get("portfolio_name") or config.get("instrument_symbol"),
        "analysis_date": analysis_date.isoformat(),
        "period": _extract_period(result_payload),
        "frequency": config.get("frequency"),
        "adjust": config.get("adjust"),
        "metrics": backtest.metrics or {},
        "data_quality": result_payload.get("data_quality") or {},
        "targets": targets,
        "ticker_mapping": _ticker_mapping(targets),
        "coverage_summary": coverage_summary,
        "warnings": warnings,
    }
