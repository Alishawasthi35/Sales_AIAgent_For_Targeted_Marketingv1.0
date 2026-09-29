"""PII-free, structured operational events for local runs and Cloud Logging."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any


def monotonic_ms() -> int:
    return time.monotonic_ns() // 1_000_000


def emit(event: str, call_id: str, **fields: Any) -> None:
    # Only pass operational fields here. Never include audio, transcripts, lead
    # details, provider credentials, or raw exception messages.
    record = {
        "severity": "INFO",
        "event": event,
        "call_id": call_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    print(json.dumps(record, ensure_ascii=True, separators=(",", ":")), flush=True)
