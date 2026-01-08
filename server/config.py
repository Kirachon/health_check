from pydantic_settings import BaseSettings
from typing import Any
import json
from pydantic import field_validator


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
    
    # Security
    BCRYPT_ROUNDS: int = 12

    # Alerting webhook
    ALERT_WEBHOOK_REQUIRE_TOKEN: bool = True
    ALERT_WEBHOOK_TOKEN: str = ""
    ALERT_EVENT_RETENTION_DAYS: int = 30

    # Device status
    # If a device hasn't heartbeated within this window, treat it as offline.
    DEVICE_OFFLINE_THRESHOLD_SECONDS: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
