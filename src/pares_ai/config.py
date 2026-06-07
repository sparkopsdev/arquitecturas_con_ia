from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    app_secret: str
    database_path: Path
    data_dir: Path
    pdf_output_dir: Path
    allowed_origins: list[str]
    token_ttl_seconds: int


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def get_settings() -> Settings:
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    pdf_output_dir = Path(os.getenv("PDF_OUTPUT_DIR", "runtime/pdf"))
    database_path = Path(os.getenv("DATABASE_PATH", "runtime/pares_ai.sqlite3"))

    data_dir.mkdir(parents=True, exist_ok=True)
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_name=os.getenv("APP_NAME", "PARES AI RAG"),
        app_env=os.getenv("APP_ENV", "local"),
        app_secret=os.getenv("APP_SECRET", "change-me-in-production"),
        database_path=database_path,
        data_dir=data_dir,
        pdf_output_dir=pdf_output_dir,
        allowed_origins=_csv(os.getenv("ALLOWED_ORIGINS", "http://localhost:8000")),
        token_ttl_seconds=int(os.getenv("TOKEN_TTL_SECONDS", "28800")),
    )
