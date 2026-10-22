"""
Application Configuration and Security Settings
Loads settings from environment variables and optional .env file using pydantic-settings.
"""

from typing import List, Union, Any
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os
import secrets


def get_default_secret_key() -> str:
    """
    Returns configured secret key from environment or generates a secure random 256-bit key.
    Never uses hardcoded or insecure fallback strings.
    """
    return os.environ.get("PATHOGUARD_SECRET_KEY") or os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)


class Settings(BaseSettings):
    PROJECT_NAME: str = "PathoGuard Clinical Intelligence API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default_factory=get_default_secret_key)

    @field_validator("DEBUG", mode="before")
    @classmethod
    def resolve_debug(cls, v: Any, info) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    # Database connection string (PostgreSQL for prod, defaults to None for SQLite)
    DATABASE_URL: Union[str, None] = None

    # Allowed CORS Origins (Frontend Dev Server & Live Server)
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]

    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    RATE_LIMIT_PER_MINUTE: int = 60
    LOG_LEVEL: str = "INFO"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://127.0.0.1:5500", "http://localhost:5500"]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
