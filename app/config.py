"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = ""

    # JWT Settings
    SECRET_KEY: str = ""
    ALGORITHM: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SHARED CONTEXT (for microservices communication)
    SHARED_CONTEXT_SECRET: str = ""
    SHARED_CONTEXT_EXPIRE_MINUTES: int = 15

    # Service-to-service auth (Authorization: Bearer <jwt>)
    SERVICE_TOKEN: str = Field(
        "", description="Shared secret used to sign/verify service JWT"
    )
    SERVICE_NAME: str = Field(
        "auth_service", description="Expected service identifier inside the service JWT"
    )

    # App Settings
    APP_NAME: str = "Auth Microservice"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = [""]

    class Config:
        env_file = ".env"
        case_sensitive = True
        # env_prefix = "AUTH_"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
