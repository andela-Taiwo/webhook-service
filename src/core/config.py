from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="WEBHOOK_",
        extra="ignore",
    )

    # --- App identity ---
    app_name: str = "webhook-service"
    environment: Literal["local", "test", "staging", "production"] = "local"
    api_v1_prefix: str = "/api/v1"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True  # False gives pretty console output for local dev

    # --- Observability (OpenTelemetry) ---
    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_traces_sample_ratio: float = 1.0  # 1.0 = sample everything (dev only)

    # --- Metrics ---
    metrics_enabled: bool = True

    database_url: str = "postgresql+asyncpg://webhook:webhook@localhost:5432/webhook"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — use this in FastAPI dependencies."""
    return Settings()


settings = get_settings()
