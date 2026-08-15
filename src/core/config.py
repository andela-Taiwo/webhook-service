from functools import lru_cache
from typing import Literal
import os

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

    # --- Database ---
    database_url: str = os.getenv('WEBHOOK_DATABASE_URL', 'postgresql+asyncpg://webhook:webhook@localhost:5432/webhook')

    # --- Message Queue ---
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    webhook_queue_name: str = "webhook_events"

    # --- Webhook Security ---
    webhook_secret_key: str = os.getenv('WEBHOOK_SECRET_KEY', 'change-this-in-production')
    webhook_signature_header: str = "X-Webhook-Signature"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — use this in FastAPI dependencies."""
    return Settings()


settings = get_settings()
