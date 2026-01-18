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
    
    # App Settings
    APP_NAME: str = "Auth Microservice"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
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
