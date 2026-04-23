"""Settings centralizadas (Pydantic Settings, carga desde `.env`)."""

from __future__ import annotations

import os
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


# Campos de Settings que librerías externas (LangChain, langchain-google-genai,
# langchain-anthropic, etc.) esperan encontrar en `os.environ`. Pydantic Settings
# los carga desde `.env` pero no los propaga al entorno del proceso; lo hacemos
# explícito para que `os.environ.get("GOOGLE_API_KEY")` en el extractor funcione.
_ENV_PROPAGATION: tuple[tuple[str, str], ...] = (
    ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    ("openai_api_key", "OPENAI_API_KEY"),
    ("google_api_key", "GOOGLE_API_KEY"),
    ("voyage_api_key", "VOYAGE_API_KEY"),
    ("ollama_base_url", "OLLAMA_BASE_URL"),
    ("serpapi_key", "SERPAPI_KEY"),
)


def _propagate_to_env(settings: "Settings") -> None:
    for attr, env in _ENV_PROPAGATION:
        val = getattr(settings, attr, "")
        if val and not os.environ.get(env):
            os.environ[env] = val


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _propagate_to_env(settings)
    return settings
