"""Application configuration via environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "TruthTrace AI"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database (MySQL)
    database_url: str = "mysql+aiomysql://root:root@localhost:3306/truthtrace"
    # Set to true for hosted MySQL providers that require SSL (Aiven is auto-detected)
    database_ssl_required: bool = False
    # Optional path to Aiven CA certificate (ca.pem from Aiven console)
    database_ssl_ca: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 8192

    # Search
    tavily_api_key: str = ""
    serper_api_key: str = ""

    # Auth (Clerk)
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # Rate limiting
    rate_limit: str = "30/minute"

    # Timeouts
    request_timeout: float = 120.0
    search_timeout: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
