from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bar, Instrument
from app.services.market_data import (
    fetch_public_bars,
    fetch_trading_calendar,
    get_public_bar_provider,
    list_public_bar_providers,
    list_trading_calendar_providers,
    to_tushare_ts_code,
    tushare_date,
    tushare_frequency,
)
from app.services.data_quality import assess_bar_completeness


def test_bar_identity_is_unique_per_instrument_frequency_timestamp_and_adjust() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        instrument = Instrument(symbol="TUNIQ01", exchange="SH", name="Unique Test")
        session.add(instrument)
        session.commit()
        session.refresh(instrument)

        timestamp = datetime.fromisoformat("2026-01-02 09:35:00")
        session.add(
            Bar(
                instrument_id=instrument.id or 0,
                frequency="5m",
                timestamp=timestamp,
                adjust="qfq",
                open=10,
                high=11,
                low=9,
                close=10.5,
                volume=1000,
            )
        )
        session.commit()

        session.add(
            Bar(
                instrument_id=instrument.id or 0,
                frequency="5m",
                timestamp=timestamp,
                adjust="hfq",
                open=10,
                high=12,
                low=8,
                close=11,
                volume=1200,
            )
        )
        session.commit()

        session.add(
            Bar(
                instrument_id=instrument.id or 0,
                frequency="5m",
                timestamp=timestamp,
                adjust="qfq",
                open=10,
                high=12,
                low=8,
                close=11,
                volume=1200,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_public_bar_provider_registry_exposes_default_akshare_provider() -> None:
    assert "akshare" in list_public_bar_providers()
    assert get_public_bar_provider("akshare")


def test_tushare_provider_contract_helpers() -> None:
    assert "tushare" in list_public_bar_providers()
    assert "tushare" in list_trading_calendar_providers()
    assert get_public_bar_provider("tushare")
    assert to_tushare_ts_code("600519", "SH") == "600519.SH"
    assert to_tushare_ts_code("000001", "SZSE") == "000001.SZ"
    assert tushare_frequency("1d") == "D"
    assert tushare_frequency("5m") == "5min"
    assert tushare_date("2026-01-02", frequency="1d") == "20260102"
    assert tushare_date("2026-01-02", frequency="5m", end_of_day=True) == "2026-01-02 23:59:59"


def test_fetch_trading_calendar_normalizes_tushare_rows() -> None:
    def fake_calendar_provider(**kwargs):
        assert kwargs["exchange"] == "SH"
        return [
            {"cal_date": "20260102", "is_open": 1},
            {"cal_date": "20260103", "is_open": 0},
            {"cal_date": "20260105", "is_open": "1"},
        ]

    dates = fetch_trading_calendar(
        provider_name="tushare",
        exchange="SH",
        start_date="2026-01-01",
        end_date="2026-01-05",
        provider=fake_calendar_provider,
    )

    assert dates == ["2026-01-02", "2026-01-05"]


def test_fetch_public_bars_normalizes_tushare_rows() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        instrument = Instrument(symbol="600519", exchange="SH", name="Kweichow Moutai")
        session.add(instrument)
        session.commit()
        session.refresh(instrument)

        def fake_tushare_provider(**kwargs):
            assert kwargs["symbol"] == "600519"
            assert kwargs["exchange"] == "SH"
            return [
                {
                    "trade_date": "20260103",
                    "open": 11,
                    "high": 12,
                    "low": 10,
                    "close": 11.5,
                    "vol": 1200,
                },
                {
                    "trade_date": "20260102",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "vol": 1000,
                },
            ]

        result = fetch_public_bars(
            session,
            instrument_symbol=instrument.symbol,
            instrument_exchange=instrument.exchange,
            instrument_id=instrument.id or 0,
            frequency="1d",
            start_date="2026-01-02",
            end_date="2026-01-03",
            adjust="qfq",
            provider_name="tushare",
            provider=fake_tushare_provider,
        )

        bars = session.exec(select(Bar).order_by(Bar.timestamp)).all()
        assert result.rows_imported == 2
        assert [bar.close for bar in bars] == [10.5, 11.5]
        assert {bar.source for bar in bars} == {"tushare"}
        assert {bar.adjust for bar in bars} == {"qfq"}


def test_daily_completeness_uses_expected_trading_calendar() -> None:
    bars = [
        Bar(
            instrument_id=1,
            frequency="1d",
            timestamp=datetime.fromisoformat("2026-01-02"),
            open=10,
            high=11,
            low=9,
            close=10.5,
            volume=1000,
        ),
        Bar(
            instrument_id=1,
            frequency="1d",
            timestamp=datetime.fromisoformat("2026-01-06"),
            open=11,
            high=12,
            low=10,
            close=11.5,
            volume=1000,
        ),
    ]

    completeness = assess_bar_completeness(
        instrument_id=1,
        frequency="1d",
        bars=bars,
        expected_trading_dates=["20260102", "20260105", "20260106"],
        calendar_source="tushare:test",
    )

    assert completeness.status == "warning"
    assert completeness.calendar_source == "tushare:test"
    assert completeness.expected_trading_days == 3
    assert completeness.expected_bar_count == 3
    assert completeness.missing_bar_count == 1
    assert completeness.missing_trading_days == ["2026-01-05"]
    assert completeness.completeness_ratio == 0.666667
    assert completeness.warnings
