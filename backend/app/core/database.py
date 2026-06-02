from collections.abc import Generator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

sqlite_path = settings.sqlite_path
if sqlite_path:
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    if engine.dialect.name == "sqlite":
        SQLModel.metadata.create_all(engine)
        from app.services.schema import upgrade_database_schema

        upgrade_database_schema(engine)
    from app.services.bootstrap import seed_data_source_providers, seed_default_admin

    with Session(engine) as session:
        seed_default_admin(session)
        seed_data_source_providers(session)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
