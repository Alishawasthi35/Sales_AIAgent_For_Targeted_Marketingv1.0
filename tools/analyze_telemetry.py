"""Summarize PII-free voice events exported from Cloud Logging or local stdout.

Usage: python tools/analyze_telemetry.py events.jsonl --cost-usd 0.42
Cost is a manually supplied total from actual provider/cloud invoices for these calls.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def percentile(values: list[int], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path, help="JSONL events or Cloud Logging JSONL export")
    parser.add_argument("--cost-usd", type=float, help="Actual combined cloud, Twilio, and Sarvam cost for these calls")
    args = parser.parse_args()
    calls: dict[str, dict] = defaultdict(lambda: {"turns": [], "error": False, "duration_ms": None, "attempts": 0, "clears": 0})
    for line in args.events.read_text(encoding="utf-8").splitlines():
        try:
            outer = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = outer.get("jsonPayload", outer)
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
                continue
        if not isinstance(event, dict) or not event.get("call_id"):
            continue
        call = calls[event["call_id"]]
        name = event.get("event")
        if name == "turn.audio_sent" and isinstance(event.get("speech_to_first_audio_sent_ms"), int):
            call["turns"].append(event["speech_to_first_audio_sent_ms"])
        elif name == "call.finished":
            call["duration_ms"] = event.get("duration_ms")
            call["attempts"] = event.get("interruption_attempts", 0)
            call["clears"] = event.get("interruption_clears", 0)
            call["error"] = bool(event.get("provider_errors"))
        elif name in {"provider.error", "turn.error"}:
            call["error"] = True

    completed = [call for call in calls.values() if isinstance(call["duration_ms"], int)]
    latency = [latency for call in calls.values() for latency in call["turns"]]
    duration_minutes = sum(call["duration_ms"] for call in completed) / 60000
    attempts = sum(call["attempts"] for call in completed)
    clears = sum(call["clears"] for call in completed)
    report = {
        "completed_calls": len(completed),
        "measured_turns": len(latency),
        "speech_end_to_first_audio_sent_ms_p50": percentile(latency, 0.5),
        "speech_end_to_first_audio_sent_ms_p95": percentile(latency, 0.95),
        "interruption_clear_rate": round(clears / attempts, 3) if attempts else None,
        "interruption_attempts": attempts,
        "call_error_rate": round(sum(call["error"] for call in completed) / len(completed), 3) if completed else None,
        "completed_call_minutes": round(duration_minutes, 2),
        "actual_cost_usd_per_minute": round(args.cost_usd / duration_minutes, 4) if args.cost_usd is not None and duration_minutes else None,
        "tool_call_accuracy": None,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
