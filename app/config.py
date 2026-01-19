"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/auth_db"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # SHARED CONTEXT (for microservices communication)
    SHARED_CONTEXT_SECRET: str = "your-shared-context-secret-change-in-production"
    SHARED_CONTEXT_EXPIRE_MINUTES: int = 15  # Short-lived tokens for service-to-service
    
    # App Settings
    APP_NAME: str = "Auth Microservice"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8001",
        "http://localhost:8080",
        "https://your-frontend-domain.com"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_prefix = "AUTH_"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
