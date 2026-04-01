from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Always load the .env from project root, regardless of current working directory.
load_dotenv(PROJECT_ROOT / ".env")


def _as_project_path(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


@dataclass(frozen=True)
class Settings:
    timezone: str = os.getenv("TIMEZONE", "Asia/Shanghai")
    daily_limit: int = int(os.getenv("DAILY_LIMIT", "10"))
    min_score: float = float(os.getenv("MIN_SCORE", "0.10"))
    dedupe_days: int = int(os.getenv("DEDUPE_DAYS", "7"))

    db_path: Path = _as_project_path(os.getenv("DB_PATH", "data/papers.db"))
    output_dir: Path = _as_project_path(os.getenv("OUTPUT_DIR", "outputs/daily"))
    xmind_dir: Path = _as_project_path(os.getenv("XMIND_DIR", "outputs/xmind"))
    log_dir: Path = _as_project_path(os.getenv("LOG_DIR", "logs"))

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    doubao_api_key: str | None = os.getenv("DOUBAO_API_KEY")
    doubao_model: str = os.getenv("DOUBAO_MODEL", "doubao-1-5-pro-32k-250115")
    doubao_base_url: str = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

    enable_arxiv: bool = os.getenv("ENABLE_ARXIV", "1") == "1"
    enable_semantic_scholar: bool = os.getenv("ENABLE_SEMANTIC_SCHOLAR", "1") == "1"
    enable_huggingface: bool = os.getenv("ENABLE_HUGGINGFACE", "1") == "1"
    semantic_scholar_api_key: str | None = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    notify_title: str = os.getenv("NOTIFY_TITLE", "AI Paper Daily")
    dashboard_url: str = os.getenv("DASHBOARD_URL", "http://127.0.0.1:8000")
    database_url: str | None = os.getenv("DATABASE_URL")


settings = Settings()


def ensure_dirs() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.xmind_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
