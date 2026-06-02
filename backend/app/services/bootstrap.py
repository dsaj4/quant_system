from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.security import find_user_by_username, hash_password
from app.models import DataSourceProvider, User
from app.services.operation_log import record_operation


def seed_default_admin(session: Session) -> None:
    settings = get_settings()
    if find_user_by_username(session, settings.admin_username):
        return

    user = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
    )
    session.add(user)
    session.commit()
    record_operation(
        session,
        action="auth.admin.seeded",
        actor="system",
        target_type="user",
        target_id=settings.admin_username,
    )


def seed_data_source_providers(session: Session) -> None:
    settings = get_settings()
    provider_defaults = [
        {
            "name": "tushare",
            "display_name": "Tushare Pro",
            "role": "primary",
            "priority": 10,
            "is_enabled": True,
            "is_configured": bool(settings.tushare_token),
            "credential_env_var": "QUANT_TUSHARE_TOKEN",
            "notes": "Primary A-share data source for the first production integration.",
        },
        {
            "name": "jqdata",
            "display_name": "JQData",
            "role": "supplement",
            "priority": 20,
            "is_enabled": False,
            "is_configured": False,
            "credential_env_var": "QUANT_JQDATA_TOKEN",
            "notes": "Reserved for later purchase and integration.",
        },
        {
            "name": "akshare",
            "display_name": "AkShare",
            "role": "fallback",
            "priority": 100,
            "is_enabled": True,
            "is_configured": True,
            "credential_env_var": "",
            "notes": "Free fallback provider.",
        },
        {
            "name": "baostock",
            "display_name": "BaoStock",
            "role": "fallback",
            "priority": 110,
            "is_enabled": False,
            "is_configured": True,
            "credential_env_var": "",
            "notes": "Reserved fallback provider; adapter not implemented in the first batch.",
        },
    ]

    for provider_default in provider_defaults:
        existing = session.exec(
            select(DataSourceProvider).where(DataSourceProvider.name == provider_default["name"])
        ).first()
        if existing:
            existing.display_name = provider_default["display_name"]
            existing.role = provider_default["role"]
            existing.priority = provider_default["priority"]
            existing.credential_env_var = provider_default["credential_env_var"]
            existing.notes = provider_default["notes"]
            if existing.name == "tushare":
                existing.is_configured = provider_default["is_configured"]
            session.add(existing)
            continue

        session.add(DataSourceProvider(**provider_default))

    session.commit()
