from datetime import datetime

from fastapi.testclient import TestClient
from pytest import approx

from app.main import app
from app.models import Bar, StrategyParameterSet
from app.services.backtest import calculate_performance_metrics, run_single_instrument_backtest


def login_token(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_instrument(client: TestClient, token: str, symbol: str) -> int:
    response = client.post(
        "/api/instruments",
        headers={"Authorization": f"Bearer {token}"},
        json={"symbol": symbol, "exchange": "SH", "name": f"{symbol} test stock", "asset_type": "stock"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_parameter_set(client: TestClient, token: str) -> int:
    response = client.post(
        "/api/strategy-parameter-sets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "strategy_id": "rolling_t_grid",
            "name": "Backtest config",
            "parameters": {"grid_percent": 1.0, "enable_ma_filter": False},
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def import_bars(client: TestClient, token: str, instrument_id: int) -> None:
    response = client.post(
        "/api/market-data/import-csv",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "instrument_id": instrument_id,
            "frequency": "5m",
            "source": "csv",
            "csv_text": (
                "timestamp,open,high,low,close,volume\n"
                "2026-01-02 09:35:00,10,10.5,9.8,10.0,1000\n"
                "2026-01-02 09:40:00,10.0,10.7,9.9,10.4,1200\n"
                "2026-01-02 09:45:00,10.4,10.9,10.2,10.8,1500\n"
                "2026-01-02 09:50:00,10.8,10.9,10.1,10.2,1300\n"
            ),
        },
    )
    assert response.status_code == 200


def import_custom_bars(client: TestClient, token: str, instrument_id: int, rows: list[tuple[str, float]]) -> None:
    csv_text = "timestamp,open,high,low,close,volume\n" + "\n".join(
        f"{timestamp},{close},{close},{close},{close},1000" for timestamp, close in rows
    )
    response = client.post(
        "/api/market-data/import-csv",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "instrument_id": instrument_id,
            "frequency": "5m",
            "source": "csv",
            "csv_text": csv_text,
        },
    )
    assert response.status_code == 200


def create_portfolio(client: TestClient, token: str, positions: list[dict]) -> int:
    response = client.post(
        "/api/portfolios",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Backtest basket",
            "description": "Fixed basket for portfolio backtest tests.",
            "positions": positions,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_performance_metrics_include_annualized_risk_and_trade_summaries() -> None:
    metrics = calculate_performance_metrics(
        equity_curve=[
            {"timestamp": "2025-01-01T00:00:00", "value": 100.0},
            {"timestamp": "2025-07-02T00:00:00", "value": 105.0},
            {"timestamp": "2026-01-01T00:00:00", "value": 110.0},
        ],
        drawdown_curve=[
            {"timestamp": "2025-01-01T00:00:00", "value": 0.0},
            {"timestamp": "2025-07-02T00:00:00", "value": -0.02},
            {"timestamp": "2026-01-01T00:00:00", "value": 0.0},
        ],
        trades=[
            {"change_percent": 2.0},
            {"change_percent": -1.0},
            {"change_percent": 4.0},
        ],
    )

    assert metrics["annualized_return"] == approx(0.1, abs=0.002)
    assert metrics["annualized_volatility"] > 0
    assert metrics["sharpe_ratio"] > 0
    assert metrics["calmar_ratio"] == approx(5, abs=0.1)
    assert metrics["return_drawdown_ratio"] == approx(5, abs=0.1)
    assert metrics["average_win"] == approx(0.03)
    assert metrics["average_loss"] == approx(-0.01)
    assert metrics["profit_loss_ratio"] == approx(3)


def test_performance_metrics_handle_empty_or_flat_series() -> None:
    metrics = calculate_performance_metrics(
        equity_curve=[{"timestamp": "2025-01-01T00:00:00", "value": 100.0}],
        drawdown_curve=[],
        trades=[],
    )

    assert metrics["annualized_return"] == 0
    assert metrics["annualized_volatility"] == 0
    assert metrics["sharpe_ratio"] == 0
    assert metrics["calmar_ratio"] == 0
    assert metrics["return_drawdown_ratio"] == 0
    assert metrics["average_win"] == 0
    assert metrics["average_loss"] == 0
    assert metrics["profit_loss_ratio"] == 0


def make_bar(timestamp: str, close: float) -> Bar:
    return Bar(
        instrument_id=1,
        frequency="1d",
        timestamp=datetime.fromisoformat(timestamp),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
    )


def make_parameter_set(parameters: dict) -> StrategyParameterSet:
    return StrategyParameterSet(
        strategy_id="rolling_t_grid",
        name="Engine config",
        parameters={
            "grid_percent": 5.0,
            "base_position_percent": 50.0,
            "trade_position_percent": 10.0,
            "enable_ma_filter": False,
            "fee_rate": 0.0,
            "slippage_bps": 0.0,
            **parameters,
        },
    )


def test_backtest_engine_applies_base_and_trade_position_percent() -> None:
    result = run_single_instrument_backtest(
        bars=[
            make_bar("2026-01-01T00:00:00", 100.0),
            make_bar("2026-01-02T00:00:00", 110.0),
            make_bar("2026-01-03T00:00:00", 99.0),
        ],
        parameter_set=make_parameter_set({}),
        initial_cash=1000,
    )

    trades = result.result_payload["trade_table"]
    assert result.result_payload["position_curve"][0]["value"] == approx(50)
    assert len(trades) == 2
    assert trades[0]["side"] == "sell"
    assert trades[0]["quantity"] == approx(0.954545, rel=1e-5)
    assert trades[0]["position_after"] < 50
    assert trades[1]["side"] == "buy"
    assert trades[1]["position_after"] > trades[0]["position_after"]
    assert result.metrics["cumulative_return"] == approx(0.0055, abs=0.0002)
    assert result.result_payload["orders"] == trades


def test_backtest_engine_records_fee_and_slippage_costs() -> None:
    bars = [
        make_bar("2026-01-01T00:00:00", 100.0),
        make_bar("2026-01-02T00:00:00", 110.0),
    ]
    no_cost = run_single_instrument_backtest(
        bars=bars,
        parameter_set=make_parameter_set({}),
        initial_cash=1000,
    )
    with_cost = run_single_instrument_backtest(
        bars=bars,
        parameter_set=make_parameter_set({"fee_rate": 0.001, "slippage_bps": 10.0}),
        initial_cash=1000,
    )

    trade = with_cost.result_payload["trade_table"][0]
    assert with_cost.metrics["cumulative_return"] < no_cost.metrics["cumulative_return"]
    assert trade["fee"] > 0
    assert trade["slippage"] > 0
    assert with_cost.result_payload["execution_assumptions"]["fees_included"] is True
    assert with_cost.result_payload["execution_assumptions"]["slippage_included"] is True


def test_admin_can_create_backtest_from_saved_parameter_set() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TBT001")
        parameter_set_id = create_parameter_set(client, token)
        import_bars(client, token, instrument_id)

        response = client.post(
            "/api/backtests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "parameter_set_id": parameter_set_id,
                "initial_cash": 100000,
            },
        )

        assert response.status_code == 200
        backtest = response.json()
        assert backtest["status"] == "succeeded"
        assert backtest["strategy_id"] == "rolling_t_grid"
        assert backtest["metrics"]["bar_count"] == 4
        assert backtest["metrics"]["cumulative_return"] == approx(0.017718)
        assert len(backtest["result_payload"]["equity_curve"]) == 4
        assert len(backtest["result_payload"]["drawdown_curve"]) == 4
        assert backtest["result_payload"]["trade_markers"]
        assert backtest["result_payload"]["orders"] == backtest["result_payload"]["trade_table"]
        assert backtest["result_payload"]["trade_table"][0]["quantity"] > 0
        assert backtest["result_payload"]["execution_assumptions"]["base_position_percent"] == 50
        assert backtest["result_payload"]["data_quality"]["status"] == "warning"
        assert backtest["result_payload"]["data_quality"]["warnings"]

        logs_response = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        actions = [item["action"] for item in logs_response.json()]
        assert "backtest.create.succeeded" in actions


def test_admin_can_create_fixed_portfolio_backtest() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        first_instrument_id = create_instrument(client, token, "TBT101")
        second_instrument_id = create_instrument(client, token, "TBT102")
        parameter_set_id = create_parameter_set(client, token)
        import_custom_bars(
            client,
            token,
            first_instrument_id,
            [
                ("2026-01-02 09:35:00", 10.0),
                ("2026-01-02 09:40:00", 10.5),
                ("2026-01-02 09:45:00", 11.0),
            ],
        )
        import_custom_bars(
            client,
            token,
            second_instrument_id,
            [
                ("2026-01-02 09:35:00", 20.0),
                ("2026-01-02 09:40:00", 19.0),
                ("2026-01-02 09:45:00", 18.0),
            ],
        )
        portfolio_id = create_portfolio(
            client,
            token,
            [
                {"instrument_id": first_instrument_id, "weight": 0.6},
                {"instrument_id": second_instrument_id, "weight": 0.4},
            ],
        )

        response = client.post(
            "/api/backtests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "portfolio_id": portfolio_id,
                "frequency": "5m",
                "parameter_set_id": parameter_set_id,
                "initial_cash": 100000,
            },
        )

        assert response.status_code == 200
        backtest = response.json()
        assert backtest["config"]["scope"] == "portfolio"
        assert backtest["config"]["portfolio_id"] == portfolio_id
        assert backtest["metrics"]["bar_count"] == 3
        assert backtest["metrics"]["cumulative_return"] == approx(0.009005)
        assert backtest["result_payload"]["scope"] == "portfolio"
        assert len(backtest["result_payload"]["portfolio_legs"]) == 2


def test_backtest_fails_clearly_when_bars_are_missing() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        instrument_id = create_instrument(client, token, "TBT002")
        parameter_set_id = create_parameter_set(client, token)

        response = client.post(
            "/api/backtests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "instrument_id": instrument_id,
                "frequency": "5m",
                "parameter_set_id": parameter_set_id,
            },
        )

        assert response.status_code == 400
        assert "No bars found" in response.json()["detail"]


def test_portfolio_backtest_fails_when_position_bars_are_missing() -> None:
    with TestClient(app) as client:
        token = login_token(client)
        first_instrument_id = create_instrument(client, token, "TBT201")
        second_instrument_id = create_instrument(client, token, "TBT202")
        parameter_set_id = create_parameter_set(client, token)
        import_custom_bars(
            client,
            token,
            first_instrument_id,
            [
                ("2026-01-02 09:35:00", 10.0),
                ("2026-01-02 09:40:00", 10.5),
            ],
        )
        portfolio_id = create_portfolio(
            client,
            token,
            [
                {"instrument_id": first_instrument_id, "weight": 0.5},
                {"instrument_id": second_instrument_id, "weight": 0.5},
            ],
        )

        response = client.post(
            "/api/backtests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "portfolio_id": portfolio_id,
                "frequency": "5m",
                "parameter_set_id": parameter_set_id,
            },
        )

        assert response.status_code == 400
        assert "No bars found for portfolio instrument" in response.json()["detail"]
