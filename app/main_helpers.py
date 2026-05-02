from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db import connect, json_dump


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def audit(
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, Any] | None = None,
    actor_type: str = "system",
    actor_id: str = "",
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs
                (id, actor_type, actor_id, action, entity_type, entity_id, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id("audit"), actor_type, actor_id, action, entity_type, entity_id, json_dump(metadata or {}), now_iso()),
        )

