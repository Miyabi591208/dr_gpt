import json
import sqlite3
from typing import Any


class StateStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_state (
                    user_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    step TEXT NOT NULL,
                    data_json TEXT NOT NULL DEFAULT '{}',
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_user_id_id
                ON chat_history (user_id, id)
                """
            )

            conn.commit()

    def get(self, user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT mode, step, data_json
                FROM user_state
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return {"mode": "", "step": "", "data": {}}

        try:
            data = json.loads(row["data_json"]) if row["data_json"] else {}
        except json.JSONDecodeError:
            data = {}

        return {
            "mode": row["mode"],
            "step": row["step"],
            "data": data,
        }

    def set(self, user_id: str, mode: str, step: str, data: dict[str, Any]) -> None:
        data_json = json.dumps(data or {}, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_state (user_id, mode, step, data_json, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    mode = excluded.mode,
                    step = excluded.step,
                    data_json = excluded.data_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, mode, step, data_json),
            )
            conn.commit()

    def clear(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
            conn.commit()

    def append_chat_message(self, user_id: str, role: str, content: str) -> None:
        role = (role or "").strip()
        content = (content or "").strip()

        if role not in {"user", "assistant", "system"}:
            raise ValueError("role must be one of: user, assistant, system")

        if not content:
            return

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_history (user_id, role, content)
                VALUES (?, ?, ?)
                """,
                (user_id, role, content),
            )
            conn.commit()

    def get_chat_history(self, user_id: str, limit: int = 10) -> list[dict[str, str]]:
        limit = max(1, int(limit))

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        # 新しい順で取っているので、OpenAIに渡すため古い順へ戻す
        rows = list(reversed(rows))

        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def clear_chat_history(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.commit()

    def trim_chat_history(self, user_id: str, keep_last: int = 20) -> None:
        keep_last = max(1, int(keep_last))

        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM chat_history
                WHERE user_id = ?
                  AND id NOT IN (
                      SELECT id
                      FROM chat_history
                      WHERE user_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
                """,
                (user_id, user_id, keep_last),
            )
            conn.commit()
