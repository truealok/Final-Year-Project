"""Application settings loaded from environment variables / `.env` file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, typed application configuration (12-factor style)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    PROJECT_NAME: str = "ResiliChain AI"
    PROJECT_DESCRIPTION: str = (
        "Intelligent Supply Chain Forecasting & Resilience Simulator - "
        "enterprise backend API."
    )
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/resilichain"
    )
    AUTO_CREATE_TABLES: bool = True

    # --- JWT / security ---
    JWT_SECRET_KEY: str = "dev-only-secret-change-me-in-production-0123456789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    # --- Rate limiting (ready; disabled by default) ---
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS value into a list."""
        raw = self.CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


settings = get_settings()
