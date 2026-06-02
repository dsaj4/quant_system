from typing import Literal

from pydantic import BaseModel, Field


class StrategyParameter(BaseModel):
    name: str
    label: str
    type: Literal["number", "integer", "boolean", "select"]
    default: float | int | bool | str
    description: str
    min_value: float | None = None
    max_value: float | None = None
    options: list[str] = Field(default_factory=list)


class StrategyTemplate(BaseModel):
    strategy_id: str
    display_name: str
    description: str
    version: str
    supported_scopes: list[Literal["single_stock", "fixed_portfolio"]]
    supported_frequencies: list[str]
    parameters: list[StrategyParameter]
    output_contract: list[str]


ROLLING_T_GRID = StrategyTemplate(
    strategy_id="rolling_t_grid",
    display_name="Rolling T / Grid Strategy",
    description=(
        "Rule-based rolling T strategy for a fixed stock or portfolio. "
        "It uses grid thresholds and an optional moving-average filter."
    ),
    version="0.1.0",
    supported_scopes=["single_stock", "fixed_portfolio"],
    supported_frequencies=["1m", "5m", "15m", "30m", "60m", "1d"],
    parameters=[
        StrategyParameter(
            name="grid_percent",
            label="Grid Percent",
            type="number",
            default=1.5,
            min_value=0.1,
            max_value=20,
            description="Price movement percentage that triggers a grid buy/sell signal.",
        ),
        StrategyParameter(
            name="base_position_percent",
            label="Base Position Percent",
            type="number",
            default=50,
            min_value=0,
            max_value=100,
            description="Baseline position percentage kept for rolling T operations.",
        ),
        StrategyParameter(
            name="trade_position_percent",
            label="Trade Position Percent",
            type="number",
            default=10,
            min_value=1,
            max_value=100,
            description="Position percentage used by each grid trade.",
        ),
        StrategyParameter(
            name="enable_ma_filter",
            label="Enable MA Filter",
            type="boolean",
            default=True,
            description="Enable moving-average trend filter before generating signals.",
        ),
        StrategyParameter(
            name="ma_window",
            label="MA Window",
            type="integer",
            default=20,
            min_value=2,
            max_value=250,
            description="Moving-average window used when the filter is enabled.",
        ),
        StrategyParameter(
            name="fee_rate",
            label="Fee Rate",
            type="number",
            default=0,
            min_value=0,
            max_value=0.05,
            description="Transaction fee rate applied to simulated fills, for example 0.001 means 0.1%.",
        ),
        StrategyParameter(
            name="slippage_bps",
            label="Slippage Bps",
            type="number",
            default=0,
            min_value=0,
            max_value=100,
            description="One-way simulated slippage in basis points applied to fill prices.",
        ),
    ],
    output_contract=[
        "metrics",
        "equity_curve",
        "benchmark_curve",
        "drawdown_curve",
        "candles",
        "trade_markers",
        "position_curve",
        "trade_table",
        "risk_disclosure",
    ],
)


def get_strategy_registry() -> list[StrategyTemplate]:
    return [ROLLING_T_GRID]


def get_strategy_template(strategy_id: str) -> StrategyTemplate | None:
    return next((strategy for strategy in get_strategy_registry() if strategy.strategy_id == strategy_id), None)


def normalize_strategy_parameters(strategy_id: str, parameters: dict) -> dict:
    template = get_strategy_template(strategy_id)
    if template is None:
        raise ValueError(f"Unknown strategy: {strategy_id}")

    known_names = {parameter.name for parameter in template.parameters}
    unknown_names = set(parameters) - known_names
    if unknown_names:
        unknown = ", ".join(sorted(unknown_names))
        raise ValueError(f"Unknown parameters for {strategy_id}: {unknown}")

    normalized = {}
    for parameter in template.parameters:
        raw_value = parameters.get(parameter.name, parameter.default)
        if parameter.type == "boolean":
            if not isinstance(raw_value, bool):
                raise ValueError(f"{parameter.name} must be a boolean")
            value = raw_value
        elif parameter.type == "integer":
            if isinstance(raw_value, bool):
                raise ValueError(f"{parameter.name} must be an integer")
            value = int(raw_value)
            if value != raw_value and not (isinstance(raw_value, float) and raw_value.is_integer()):
                raise ValueError(f"{parameter.name} must be an integer")
        elif parameter.type == "number":
            if isinstance(raw_value, bool):
                raise ValueError(f"{parameter.name} must be a number")
            value = float(raw_value)
        elif parameter.type == "select":
            value = str(raw_value)
            if value not in parameter.options:
                raise ValueError(f"{parameter.name} must be one of: {', '.join(parameter.options)}")
        else:
            value = raw_value

        if parameter.min_value is not None and isinstance(value, int | float) and value < parameter.min_value:
            raise ValueError(f"{parameter.name} must be >= {parameter.min_value}")
        if parameter.max_value is not None and isinstance(value, int | float) and value > parameter.max_value:
            raise ValueError(f"{parameter.name} must be <= {parameter.max_value}")

        normalized[parameter.name] = value

    return normalized
