from fastapi import APIRouter
from sqlmodel import select

from app.core.database import engine
from app.core.database import SessionDep
from app.models import DataSourceProvider, Instrument
from app.scheduler.market_data import scheduler
from app.services.market_data import list_public_bar_providers
from app.services.schema import check_database_schema

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(session: SessionDep) -> dict[str, object]:
    instrument_count = len(session.exec(select(Instrument.id)).all())
    schema_report = check_database_schema(engine)
    scheduler_status = "running" if scheduler.running else "stopped"
    adapter_providers = list_public_bar_providers()
    configured_providers = session.exec(select(DataSourceProvider).order_by(DataSourceProvider.priority)).all()
    enabled_provider_names = [provider.name for provider in configured_providers if provider.is_enabled]
    primary_provider_config = next((provider for provider in configured_providers if provider.role == "primary"), None)
    primary_provider = primary_provider_config.name if primary_provider_config else None
    dependency_statuses = {
        "database": "ok",
        "schema": schema_report.status,
        "scheduler": scheduler_status,
        "public_data_providers": "ok" if configured_providers else "missing",
        "primary_data_provider": (
            "configured"
            if primary_provider_config and primary_provider_config.is_configured
            else "not_configured"
            if primary_provider_config
            else "missing"
        ),
    }
    status = "ok" if all(value in {"ok", "running", "configured"} for value in dependency_statuses.values()) else "degraded"
    return {
        "status": status,
        "database": "ok",
        "dependencies": dependency_statuses,
        "scheduler": {
            "status": scheduler_status,
            "job_count": len(scheduler.get_jobs()) if scheduler.running else 0,
        },
        "public_data": {
            "providers": [provider.name for provider in configured_providers],
            "enabled_providers": enabled_provider_names,
            "adapter_providers": adapter_providers,
            "default_provider": primary_provider,
            "primary_provider": {
                "name": primary_provider,
                "is_configured": bool(primary_provider_config and primary_provider_config.is_configured),
                "adapter_available": bool(primary_provider and primary_provider in adapter_providers),
            },
            "configured": {provider.name: provider.is_configured for provider in configured_providers},
            "details": [
                {
                    "name": provider.name,
                    "display_name": provider.display_name,
                    "role": provider.role,
                    "priority": provider.priority,
                    "is_enabled": provider.is_enabled,
                    "is_configured": provider.is_configured,
                    "adapter_available": provider.name in adapter_providers,
                }
                for provider in configured_providers
            ],
        },
        "schema": {
            "status": schema_report.status,
            "missing_tables": schema_report.missing_tables,
            "missing_columns": schema_report.missing_columns,
        },
        "instrument_count": instrument_count,
    }
