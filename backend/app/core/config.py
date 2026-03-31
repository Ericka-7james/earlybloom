from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    # -----------------------------
    # Supabase
    # -----------------------------
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_SECRET_KEY: str | None = os.getenv("SUPABASE_SECRET_KEY")
    SUPABASE_PUBLISHABLE_KEY: str | None = os.getenv("SUPABASE_PUBLISHABLE_KEY")

    # -----------------------------
    # App behavior
    # -----------------------------
    JOB_DATA_MODE: str = os.getenv("JOB_DATA_MODE", "mock").strip().lower()


settings = Settings()