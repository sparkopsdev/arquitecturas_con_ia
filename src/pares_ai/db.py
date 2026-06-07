from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    year_from INTEGER,
                    year_to INTEGER,
                    raw_text TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    event_name TEXT NOT NULL,
                    date_text TEXT,
                    summary TEXT NOT NULL,
                    people TEXT NOT NULL DEFAULT '[]',
                    places TEXT NOT NULL DEFAULT '[]',
                    ships TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.65,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    fact_id INTEGER REFERENCES facts(id) ON DELETE SET NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_facts_event ON facts(event_name);
                CREATE INDEX IF NOT EXISTS idx_documents_year_from ON documents(year_from);
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);
                """
            )

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            return int(cur.lastrowid)

    def query_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def insert_document(
        self,
        title: str,
        source_name: str,
        year_from: int | None,
        year_to: int | None,
        raw_text: str,
        content_hash: str,
    ) -> int:
        return self.execute(
            """
            INSERT INTO documents(title, source_name, year_from, year_to, raw_text, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, source_name, year_from, year_to, raw_text, content_hash, utc_now()),
        )

    def insert_fact(
        self,
        document_id: int,
        event_name: str,
        date_text: str,
        summary: str,
        people: list[str],
        places: list[str],
        ships: list[str],
        confidence: float,
    ) -> int:
        return self.execute(
            """
            INSERT INTO facts(document_id, event_name, date_text, summary, people, places, ships, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                event_name,
                date_text,
                summary,
                json.dumps(people, ensure_ascii=False),
                json.dumps(places, ensure_ascii=False),
                json.dumps(ships, ensure_ascii=False),
                confidence,
                utc_now(),
            ),
        )

    def insert_chunk(self, document_id: int, fact_id: int | None, text: str) -> int:
        return self.execute(
            """
            INSERT INTO chunks(document_id, fact_id, text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (document_id, fact_id, text, utc_now()),
        )

    def add_audit(self, actor: str, role: str, action: str, detail: dict[str, Any] | str) -> int:
        if not isinstance(detail, str):
            detail = json.dumps(detail, ensure_ascii=False)
        return self.execute(
            """
            INSERT INTO audit_logs(actor, role, action, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (actor, role, action, detail, utc_now()),
        )
