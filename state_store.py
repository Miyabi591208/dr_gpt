import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any


class StateStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_state (
                    user_id TEXT PRIMARY KEY,
                    mode TEXT,
                    step TEXT,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, user_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, mode, step, data_json, updated_at FROM user_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if not row:
            return {"user_id": user_id, "mode": None, "step": None, "data": {}}

        return {
            "user_id": row["user_id"],
            "mode": row["mode"],
            "step": row["step"],
            "data": json.loads(row["data_json"] or "{}"),
            "updated_at": row["updated_at"],
        }

    def set(self, user_id: str, mode: str | None, step: str | None, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, ensure_ascii=False)

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_state (user_id, mode, step, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    mode = excluded.mode,
                    step = excluded.step,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, mode, step, payload, now),
            )
            conn.commit()

    def clear(self, user_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
            conn.commit()