from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import BacktestRun, Instrument, Portfolio, PortfolioInstrument, TaskStatus
from app.services.narrative_inputs import (
    build_narrative_input_summary,
    extract_backtest_end_date,
    map_instrument_to_tradingagents_ticker,
)


def test_a_share_ticker_mapping_uses_yahoo_suffixes() -> None:
    assert map_instrument_to_tradingagents_ticker(Instrument(symbol="600519", exchange="SH", name="贵州茅台")) == (
        "600519.SS"
    )
    assert map_instrument_to_tradingagents_ticker(Instrument(symbol="600519", exchange="SSE", name="贵州茅台")) == (
        "600519.SS"
    )
    assert map_instrument_to_tradingagents_ticker(Instrument(symbol="000001", exchange="SZ", name="平安银行")) == (
        "000001.SZ"
    )
    assert map_instrument_to_tradingagents_ticker(Instrument(symbol="000001", exchange="SZSE", name="平安银行")) == (
        "000001.SZ"
    )


def test_unsupported_exchange_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Unsupported exchange"):
        map_instrument_to_tradingagents_ticker(Instrument(symbol="AAPL", exchange="NASDAQ", name="Apple"))


def test_single_instrument_input_summary_includes_backtest_context() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        instrument = Instrument(symbol="600519", exchange="SH", name="贵州茅台")
        session.add(instrument)
        session.commit()
        session.refresh(instrument)
        backtest = BacktestRun(
            strategy_id="rolling_t_grid",
            status=TaskStatus.succeeded,
            config={
                "scope": "instrument",
                "instrument_id": instrument.id,
                "instrument_symbol": instrument.symbol,
                "frequency": "5m",
            },
            metrics={"bar_count": 60, "trade_count": 4},
            result_payload={
                "equity_curve": [
                    {"timestamp": "2026-01-02T09:35:00", "value": 100000},
                    {"timestamp": "2026-01-31T15:00:00", "value": 105000},
                ],
                "data_quality": {"status": "ok", "warnings": []},
            },
        )
        session.add(backtest)
        session.commit()
        session.refresh(backtest)

        summary = build_narrative_input_summary(
            session,
            backtest,
            analysis_date=date(2026, 2, 1),
            today=date(2026, 6, 3),
        )

    assert summary["backtest_id"] == backtest.id
    assert summary["strategy_id"] == "rolling_t_grid"
    assert summary["target_scope"] == "instrument"
    assert summary["analysis_date"] == "2026-02-01"
    assert summary["period"]["end"] == "2026-01-31T15:00:00"
    assert summary["data_quality"]["status"] == "ok"
    assert summary["ticker_mapping"] == {"600519.SH": "600519.SS"}
    assert summary["targets"][0]["name"] == "贵州茅台"


def test_portfolio_input_summary_covers_top_three_weighted_instruments() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        instruments = [
            Instrument(symbol="600519", exchange="SH", name="贵州茅台"),
            Instrument(symbol="000001", exchange="SZ", name="平安银行"),
            Instrument(symbol="000002", exchange="SZSE", name="万科A"),
            Instrument(symbol="601318", exchange="SSE", name="中国平安"),
        ]
        session.add_all(instruments)
        session.commit()
        for instrument in instruments:
            session.refresh(instrument)

        portfolio = Portfolio(name="核心组合")
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)

        weights = [0.2, 0.5, 0.3, 0.1]
        for instrument, weight in zip(instruments, weights, strict=True):
            session.add(
                PortfolioInstrument(
                    portfolio_id=portfolio.id,
                    instrument_id=instrument.id,
                    weight=weight,
                )
            )
        session.commit()

        backtest = BacktestRun(
            strategy_id="rolling_t_grid",
            status=TaskStatus.succeeded,
            config={
                "scope": "portfolio",
                "portfolio_id": portfolio.id,
                "portfolio_name": portfolio.name,
                "positions": [
                    {"instrument_id": instrument.id, "symbol": instrument.symbol, "weight": weight}
                    for instrument, weight in zip(instruments, weights, strict=True)
                ],
                "frequency": "5m",
            },
            metrics={"bar_count": 60, "trade_count": 4},
            result_payload={"data_quality": {"status": "ok", "warnings": []}},
        )
        session.add(backtest)
        session.commit()
        session.refresh(backtest)

        summary = build_narrative_input_summary(
            session,
            backtest,
            analysis_date=date(2026, 6, 3),
            today=date(2026, 6, 3),
        )

    assert summary["target_scope"] == "portfolio"
    assert summary["coverage_summary"]["covered_count"] == 3
    assert summary["coverage_summary"]["total_position_count"] == 4
    assert [target["symbol"] for target in summary["targets"]] == ["000001", "000002", "600519"]
    assert summary["ticker_mapping"] == {
        "000001.SZ": "000001.SZ",
        "000002.SZSE": "000002.SZ",
        "600519.SH": "600519.SS",
    }


def test_analysis_date_later_than_today_rejects() -> None:
    backtest = BacktestRun(strategy_id="rolling_t_grid", status=TaskStatus.succeeded)
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        with pytest.raises(ValueError, match="Analysis date cannot be later than current date"):
            build_narrative_input_summary(
                session,
                backtest,
                analysis_date=date(2026, 6, 4),
                today=date(2026, 6, 3),
            )


def test_analysis_date_before_backtest_end_records_warning() -> None:
    backtest = BacktestRun(
        strategy_id="rolling_t_grid",
        status=TaskStatus.succeeded,
        config={"scope": "instrument", "instrument_id": 1, "instrument_symbol": "600519"},
        result_payload={
            "equity_curve": [
                {"timestamp": "2026-06-01T09:35:00", "value": 100000},
                {"timestamp": "2026-06-03T15:00:00", "value": 101000},
            ],
            "data_quality": {"status": "ok", "warnings": []},
        },
    )
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Instrument(id=1, symbol="600519", exchange="SH", name="贵州茅台"))
        session.commit()
        summary = build_narrative_input_summary(
            session,
            backtest,
            analysis_date=date(2026, 6, 2),
            today=date(2026, 6, 3),
        )

    assert summary["period"]["end"] == "2026-06-03T15:00:00"
    assert summary["warnings"] == ["Analysis date is earlier than the backtest end date."]


def test_extract_backtest_end_date_uses_equity_curve_then_candles() -> None:
    assert extract_backtest_end_date(
        {"equity_curve": [{"timestamp": "2026-01-02T09:35:00"}, {"timestamp": "2026-01-03T15:00:00"}]}
    ) == date(2026, 1, 3)
    assert extract_backtest_end_date({"candles": [{"timestamp": "2026-01-04T15:00:00"}]}) == date(2026, 1, 4)
