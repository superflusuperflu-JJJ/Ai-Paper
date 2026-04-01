from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, text

from app.models.paper import Paper


class PaperDB:
    def __init__(self, db_path: Path, database_url: str | None = None) -> None:
        self.db_path = db_path
        self.database_url = database_url
        self.engine = self._build_engine()
        self._init_db()

    def _build_engine(self):
        if self.database_url:
            return create_engine(self.database_url, future=True, pool_pre_ping=True)
        sqlite_url = f"sqlite:///{self.db_path}"
        return create_engine(sqlite_url, future=True)

    def _init_db(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS daily_runs (
                        run_date TEXT PRIMARY KEY,
                        papers_json TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

    def upsert_daily(self, run_date: date, papers: list[Paper]) -> None:
        payload = json.dumps([p.to_dict() for p in papers], ensure_ascii=False)
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO daily_runs(run_date, papers_json)
                    VALUES(:run_date, :papers_json)
                    ON CONFLICT(run_date) DO UPDATE
                    SET papers_json = excluded.papers_json, created_at = CURRENT_TIMESTAMP
                    """
                ),
                {"run_date": run_date.isoformat(), "papers_json": payload},
            )

    def get_daily(self, run_date: date) -> list[dict]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT papers_json FROM daily_runs WHERE run_date = :run_date"),
                {"run_date": run_date.isoformat()},
            ).fetchone()
            if not row:
                return []
            return json.loads(row[0])

    def list_recent_days(self, limit: int = 30) -> list[dict]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT run_date, created_at FROM daily_runs ORDER BY run_date DESC LIMIT :limit"),
                {"limit": limit},
            ).fetchall()
            return [{"run_date": r[0], "created_at": str(r[1])} for r in rows]

    def get_recent_titles(self, days: int) -> set[str]:
        if days <= 0:
            return set()
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT papers_json FROM daily_runs WHERE run_date >= :cutoff"),
                {"cutoff": cutoff},
            ).fetchall()
        titles: set[str] = set()
        for (payload,) in rows:
            try:
                items = json.loads(payload)
            except Exception:
                continue
            for p in items or []:
                title = str(p.get("title", "")).strip().lower()
                if title:
                    titles.add(title)
        return titles
