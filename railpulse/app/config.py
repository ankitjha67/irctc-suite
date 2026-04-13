"""Settings loaded from environment via pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "RailPulse"
    env: str = "dev"  # dev | staging | prod
    secret_key: str = "change-me"

    # Database
    database_url: str = "postgresql+psycopg://railpulse:railpulse@localhost:5432/railpulse"
    redis_url: str = "redis://localhost:6379/0"

    # RapidAPI — primary + fallback providers
    rapidapi_key: str = ""
    rapidapi_primary_host: str = "irctc1.p.rapidapi.com"
    rapidapi_fallback_host: str = "irctc-indian-railway-pnr-status.p.rapidapi.com"

    # Rate limits
    free_predictions_per_day: int = 5
    free_tracked_pnrs: int = 2
    pro_predictions_per_day: int = 100
    pro_tracked_pnrs: int = 20

    # Model
    model_path: str = "models/v0_logistic.pkl"
    model_version: str = "v0.1.0"

    # Polling
    poll_batch_size: int = 20
    poll_interval_seconds: int = 3600   # 1 hour
    poll_rate_per_second: float = 3.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
