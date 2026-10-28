import os
import sqlite3
from typing import Any

from gdss.logger import get_logger

logger = get_logger("gdss.storage.db")


class RuntimeDB:
    def __init__(self, db_path: str = ".gdss/runtime.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        logger.debug("RuntimeDB initialized at %s", self.db_path)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS branches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER,
                    name TEXT NOT NULL,
                    remote_name TEXT,
                    is_local BOOLEAN DEFAULT 0,
                    last_commit_hash TEXT,
                    sync_status TEXT,
                    last_sync TIMESTAMP,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER,
                    branch_name TEXT,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL, -- 'local' or 'remote'
                    payload TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    repo_id INTEGER,
                    packet TEXT NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES events(id),
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                );

                CREATE TABLE IF NOT EXISTS hierarchies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id INTEGER,
                    config_payload TEXT NOT NULL,
                    FOREIGN KEY (repo_id) REFERENCES repositories(id)
                );
            """)

    def register_repository(self, name: str, path: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO repositories (name, path) VALUES (?, ?)", (name, path)
            )
            if cursor.rowcount == 0:
                # Already exists, fetch ID
                cursor = conn.execute("SELECT id FROM repositories WHERE path = ?", (path,))
                return cursor.fetchone()["id"]
            return cursor.lastrowid

    def get_repositories(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM repositories")
            return [dict(row) for row in cursor.fetchall()]

    def register_branch(
        self, repo_id: int, name: str, remote_name: str | None = None, is_local: bool = False
    ):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO branches (repo_id, name, remote_name, is_local) VALUES (?, ?, ?, ?)",
                (repo_id, name, remote_name, 1 if is_local else 0),
            )

    def get_branches(self, repo_id: int) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM branches WHERE repo_id = ?", (repo_id,))
            return [dict(row) for row in cursor.fetchall()]
