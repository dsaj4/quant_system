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
    trading_agents_enabled: bool = False
    trading_agents_llm_provider: str = ""
    trading_agents_deep_think_llm: str = ""
    trading_agents_quick_think_llm: str = ""
    trading_agents_output_language: str = "Chinese"
    trading_agents_max_debate_rounds: int = 1
    trading_agents_max_risk_rounds: int = 1
    trading_agents_checkpoint_enabled: bool = False
    trading_agents_data_vendor: str = "yfinance"
    trading_agents_timeout_seconds: int = 900
    trading_agents_results_dir: str = "./data/tradingagents/logs"
    trading_agents_cache_dir: str = "./data/tradingagents/cache"
    trading_agents_memory_log_path: str = "./data/tradingagents/memory/trading_memory.md"
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
        extra="ignore",
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
