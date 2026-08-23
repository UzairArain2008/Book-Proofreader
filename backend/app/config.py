"""
Application configuration.

All configurable values are sourced from environment variables (see .env.example).
Nothing secret (API keys, etc.) is ever hardcoded here.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./storage/proofreader.db"

    # --- Uploads / limits ---
    MAX_FILE_SIZE_MB: int = 500
    MAX_CONCURRENT_PAGES: int = 3

    # --- Rendering ---
    PAGE_RENDER_DPI: int = 200

    # --- Storage / retention ---
    STORAGE_DIR: str = "./storage"
    DELETE_TEMP_FILES: bool = True

    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # --- Gemini retry / backoff ---
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_TIMEOUT_SECONDS: int = 60

    # --- Gemini rate pacing ---
    # Caps outgoing requests-per-minute to stay under your API plan's quota
    # (Gemini's free tier is 15 req/min per model as of writing). Raise this
    # if you're on a paid plan with a higher limit.
    GEMINI_REQUESTS_PER_MINUTE: int = 15

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def uploads_path(self) -> Path:
        p = self.storage_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def pages_path(self) -> Path:
        p = self.storage_path / "pages"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_path(self) -> Path:
        p = self.storage_path / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
