from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent
APP_VERSION = "3.0.0-dev.1"


def default_runtime_alias() -> Path:
    # ASCII alias for tools that cannot open Cyrillic paths (FAISS, Android Emulator).
    if os.name == "nt":
        return Path(f"{ROOT.drive}\\turism_hab_v3_runtime")
    return ROOT / ".runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Открой Хабаровский край"
    app_env: str = "development"
    app_secret: str = "development-only-change-me"
    admin_email: str = "admin@khab.local"
    admin_password: str = "change-me-before-public-use"
    api_port: int = 8100
    streamlit_port: int = 8601
    expo_port: int = 8082
    cors_origins: str = (
        "http://localhost:8082,http://localhost:8100,http://localhost:8601,http://localhost:19006"
    )
    database_url: str = "sqlite:///runtime/users.db"
    catalog_path: Path = ROOT / "catalog" / "objects.json"
    manifest_path: Path = ROOT / "dataset" / "manifest.csv"
    index_path: Path = ROOT / "artifacts" / "index.faiss"
    index_metadata_path: Path = ROOT / "artifacts" / "index_metadata.json"
    model_cache_dir: Path = ROOT / "artifacts" / "model_cache"
    content_dir: Path = ROOT / "content"
    knowledge_db_path: Path = ROOT / "runtime" / "knowledge" / "knowledge.sqlite"
    runtime_alias_dir: Path = Field(default_factory=default_runtime_alias)
    model_name: str = "ViT-B-16"
    model_pretrained: str = "openai"
    device: str = "auto"
    max_upload_mb: int = Field(default=10, ge=1, le=50)

    assistant_enabled: bool = True
    assistant_rate_limit_per_minute: int = Field(default=20, ge=1, le=1000)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    ollama_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    ollama_temperature: float = Field(default=0.2, ge=0, le=1)
    ollama_max_tokens: int = Field(default=350, ge=32, le=2048)

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def absolute(self, path: str | Path) -> Path:
        value = Path(path)
        return value if value.is_absolute() else ROOT / value


@lru_cache
def get_settings() -> Settings:
    return Settings()
