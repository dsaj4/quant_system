from fastapi import APIRouter

from app.api import (
    auth,
    backtests,
    health,
    instruments,
    market_data,
    market_data_schedules,
    operation_logs,
    paper_runs,
    portfolios,
    snapshots,
    strategies,
    strategy_parameter_sets,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(backtests.router)
api_router.include_router(health.router)
api_router.include_router(instruments.router)
api_router.include_router(market_data.router)
api_router.include_router(market_data_schedules.router)
api_router.include_router(operation_logs.router)
api_router.include_router(paper_runs.router)
api_router.include_router(portfolios.router)
api_router.include_router(snapshots.router)
api_router.include_router(strategies.router)
api_router.include_router(strategy_parameter_sets.router)
