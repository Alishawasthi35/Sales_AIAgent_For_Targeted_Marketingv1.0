from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.config import settings


def connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    with connect() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        _apply_lightweight_migrations(conn)


def _apply_lightweight_migrations(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()}
    campaign_columns = {
        "agent_persona": "TEXT NOT NULL DEFAULT 'friendly, concise, consultative sales assistant'",
        "opening_script": "TEXT NOT NULL DEFAULT ''",
        "qualification_questions_json": "TEXT NOT NULL DEFAULT '[]'",
        "objection_responses_json": "TEXT NOT NULL DEFAULT '{}'",
    }
    for name, ddl in campaign_columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE campaigns ADD COLUMN {name} {ddl}")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key, value in list(data.items()):
        if key.endswith("_json") and isinstance(value, str):
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                pass
    return data


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) or {} for row in rows]


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)

