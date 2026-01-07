from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Health Monitor API"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://monitor_user:monitor_pass@localhost:5432/health_monitor"
    
    # VictoriaMetrics
    VICTORIA_METRICS_URL: str = "http://localhost:8428"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production-minimum-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Security
    BCRYPT_ROUNDS: int = 12
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
