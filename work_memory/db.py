from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Iterable

from .utils import utc_now


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  uri TEXT NOT NULL,
  text_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(workspace_id, source_hash)
);

CREATE TABLE IF NOT EXISTS wiki_pages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  page_key TEXT NOT NULL,
  title TEXT NOT NULL,
  uri TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(workspace_id, project_id, page_key)
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  conflict_key TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self.session() as conn:
            conn.executescript(SCHEMA)

    def add_event(self, workspace_id: str, project_id: str, event_type: str, payload: str) -> None:
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO events(workspace_id, project_id, event_type, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (workspace_id, project_id, event_type, payload, utc_now()),
            )

    def list_events(
        self,
        workspace_id: str,
        project_id: str,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[sqlite3.Row]:
        with self.session() as conn:
            if event_type is None:
                rows = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE workspace_id = ? AND project_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (workspace_id, project_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM events
                    WHERE workspace_id = ? AND project_id = ? AND event_type = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (workspace_id, project_id, event_type, limit),
                ).fetchall()
        return rows

    def list_projects(self, workspace_id: str) -> list[str]:
        with self.session() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT project_id FROM sources WHERE workspace_id = ?
                UNION
                SELECT DISTINCT project_id FROM wiki_pages WHERE workspace_id = ?
                ORDER BY project_id
                """,
                (workspace_id, workspace_id),
            ).fetchall()
        return [row["project_id"] for row in rows]

    def upsert_source(
        self,
        workspace_id: str,
        project_id: str,
        title: str,
        source_type: str,
        source_hash: str,
        uri: str,
        text_path: str,
    ) -> int:
        now = utc_now()
        with self.session() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sources(
                  workspace_id, project_id, title, source_type, source_hash, uri, text_path, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, project_id, title, source_type, source_hash, uri, text_path, now),
            )
            row = conn.execute(
                "SELECT id FROM sources WHERE workspace_id = ? AND source_hash = ?",
                (workspace_id, source_hash),
            ).fetchone()
        return int(row["id"])

    def list_sources(self, workspace_id: str, project_id: str) -> list[sqlite3.Row]:
        with self.session() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sources
                WHERE workspace_id = ? AND project_id = ?
                ORDER BY created_at DESC
                """,
                (workspace_id, project_id),
            ).fetchall()
        return rows

    def upsert_page(
        self, workspace_id: str, project_id: str, page_key: str, title: str, uri: str
    ) -> None:
        now = utc_now()
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO wiki_pages(workspace_id, project_id, page_key, title, uri, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, project_id, page_key)
                DO UPDATE SET title=excluded.title, uri=excluded.uri, updated_at=excluded.updated_at
                """,
                (workspace_id, project_id, page_key, title, uri, now),
            )

    def list_pages(self, workspace_id: str, project_id: str) -> list[sqlite3.Row]:
        with self.session() as conn:
            rows = conn.execute(
                """
                SELECT * FROM wiki_pages
                WHERE workspace_id = ? AND project_id = ?
                ORDER BY page_key
                """,
                (workspace_id, project_id),
            ).fetchall()
        return rows

    def add_conversation(
        self, workspace_id: str, project_id: str, question: str, answer: str
    ) -> None:
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO conversations(workspace_id, project_id, question, answer, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (workspace_id, project_id, question, answer, utc_now()),
            )

    def upsert_conflicts(
        self, workspace_id: str, project_id: str, conflicts: Iterable[tuple[str, str]]
    ) -> None:
        now = utc_now()
        with self.session() as conn:
            for key, description in conflicts:
                existing = conn.execute(
                    """
                    SELECT id FROM conflicts
                    WHERE workspace_id = ? AND project_id = ? AND conflict_key = ?
                    """,
                    (workspace_id, project_id, key),
                ).fetchone()
                if existing:
                    continue
                conn.execute(
                    """
                    INSERT INTO conflicts(
                      workspace_id, project_id, conflict_key, description, status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, 'open', ?, ?)
                    """,
                    (workspace_id, project_id, key, description, now, now),
                )

    def open_conflicts(self, workspace_id: str, project_id: str) -> list[sqlite3.Row]:
        with self.session() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conflicts
                WHERE workspace_id = ? AND project_id = ? AND status = 'open'
                ORDER BY created_at DESC
                """,
                (workspace_id, project_id),
            ).fetchall()
        return rows

    def resolve_conflict(
        self, workspace_id: str, project_id: str, conflict_id: int, resolution: str
    ) -> bool:
        now = utc_now()
        with self.session() as conn:
            cursor = conn.execute(
                """
                UPDATE conflicts
                SET status = 'resolved', description = description || ? , updated_at = ?
                WHERE id = ? AND workspace_id = ? AND project_id = ? AND status = 'open'
                """,
                (f"\n处理结果：{resolution}", now, conflict_id, workspace_id, project_id),
            )
            rowcount = cursor.rowcount
        return rowcount > 0
