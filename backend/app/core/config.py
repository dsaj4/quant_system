from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Quant System API"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    admin_username: str = "admin"
    admin_password: str = "admin"
    database_url: str = "sqlite:///./data/quant_system.db"
    tushare_token: str = ""
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5183",
        "http://localhost:5184",
        "http://127.0.0.1:5183",
        "http://127.0.0.1:5184",
    ]

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_prefix="QUANT_",
        case_sensitive=False,
    )

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///./"
        if not self.database_url.startswith(prefix):
            return None
        return Path(self.database_url.removeprefix(prefix))


@lru_cache
def get_settings() -> Settings:
    return Settings()
