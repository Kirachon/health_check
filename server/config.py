from typing import Any
import json
import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Health Monitor API"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://monitor_user:monitor_pass@localhost:5433/health_monitor"

    # VictoriaMetrics
    VICTORIA_METRICS_URL: str = "http://localhost:9090"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production-minimum-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # Security
    BCRYPT_ROUNDS: int = 12

    # Alerting webhook
    ALERT_WEBHOOK_REQUIRE_TOKEN: bool = True
    ALERT_WEBHOOK_TOKEN: str = ""
    ALERT_EVENT_RETENTION_DAYS: int = 30

    # Device status
    # If a device hasn't heartbeated within this window, treat it as offline.
    DEVICE_OFFLINE_THRESHOLD_SECONDS: int = 90

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def _parse_cors_origins(cls, v: Any):
        # Allow env var forms:
        # - JSON list: ["http://localhost:5174", ...]
        # - Comma-separated: http://localhost:5174,http://localhost:5173
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except json.JSONDecodeError:
                    pass
            return [part.strip() for part in raw.split(",") if part.strip()]
        return v

    @field_validator("ALERT_WEBHOOK_TOKEN")
    def _strip_webhook_token(cls, v: str):
        return (v or "").strip()

    @model_validator(mode="after")
    def _validate_webhook_config(self):
        min_len = 32
        recommended_len = 64  # 32 bytes as hex
        token = (self.ALERT_WEBHOOK_TOKEN or "").strip()
        if self.ALERT_WEBHOOK_REQUIRE_TOKEN:
            if not token:
                logging.getLogger(__name__).warning(
                    "ALERT_WEBHOOK_REQUIRE_TOKEN is true but ALERT_WEBHOOK_TOKEN is empty; webhook ingestion will fail until set."
                )
            elif len(token) < min_len:
                logging.getLogger(__name__).warning(
                    f"ALERT_WEBHOOK_TOKEN appears short (<{min_len} chars). Use a strong random token (recommended: {recommended_len}+ chars)."
                )
        elif token and len(token) < min_len:
            logging.getLogger(__name__).warning(
                f"ALERT_WEBHOOK_TOKEN appears short (<{min_len} chars). Use a strong random token (recommended: {recommended_len}+ chars)."
            )
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
