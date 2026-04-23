"""Settings centralizadas (Pydantic Settings, carga desde `.env`)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:stark@localhost:5434/starkvix"
    )

    # LLM providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    voyage_api_key: str = ""

    # Local runtimes
    ollama_base_url: str = "http://localhost:11434"

    # Papers
    serpapi_key: str = ""
    arxiv_rate_limit: int = 3

    # App
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8080,http://localhost:8081"
    default_execution_mode: str = "local"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
