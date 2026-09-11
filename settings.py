from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8")

    app_name: str = "Открой Хабаровский край"
    app_env: str = "development"
    app_secret: str = "development-only-change-me"
    admin_email: str = "admin@khab.local"
    admin_password: str = "change-me-before-public-use"
    cors_origins: str = "http://localhost:8081,http://localhost:19006,http://localhost:8501"
    database_url: str = "sqlite:///runtime/users.db"
    catalog_path: Path = ROOT / "catalog" / "objects.json"
    manifest_path: Path = ROOT / "dataset" / "manifest.csv"
    index_path: Path = ROOT / "artifacts" / "index.faiss"
    index_metadata_path: Path = ROOT / "artifacts" / "index_metadata.json"
    model_cache_dir: Path = ROOT / "artifacts" / "model_cache"
    model_name: str = "ViT-B-16"
    model_pretrained: str = "openai"
    device: str = "auto"
    max_upload_mb: int = Field(default=10, ge=1, le=50)

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def absolute(self, path: str | Path) -> Path:
        value = Path(path)
        return value if value.is_absolute() else ROOT / value


@lru_cache
def get_settings() -> Settings:
    return Settings()
