"""
ADAPT — Application Configuration

All settings loaded from environment variables via pydantic-settings.
Nothing is hardcoded — every tunable value comes from .env or defaults here.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "ADAPT"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-to-a-strong-random-secret-key-in-production"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ---- Database ----
    database_url: str = "sqlite+aiosqlite:///./adapt.db"
    database_url_sync: str = "sqlite:///./adapt.db"

    # ---- JWT ----
    jwt_secret_key: str = "change-this-to-a-strong-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # ---- LLM Provider ----
    llm_provider: str = "gemini"  # "gemini" or "openai"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.3
    gemini_max_tokens: int = 8192

    # OpenAI (optional fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 4096

    # ---- Embedding Provider ----
    embedding_provider: str = "gemini"  # "gemini" or "openai"
    gemini_embedding_model: str = "gemini-embedding-2"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 768  # 768 for gemini-embedding-2, 1536 for OpenAI

    # ---- File Storage ----
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    knowledge_base_dir: str = "./knowledge_base/institutional"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # ---- Institution ----
    institution_name: str = "Sample University"
    institution_department: str = "Department of Computer Engineering"
    institution_logo_path: Optional[str] = None

    # ---- Academic ----
    academic_year: str = "2024-25"
    current_semester: str = "Even"

    # ---- Background Tasks ----
    max_concurrent_tasks: int = 5

    # ---- Logging ----
    log_level: str = "INFO"
    log_file: str = "logs/adapt.log"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
