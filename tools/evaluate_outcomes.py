"""Reproducible, offline baseline for the current rule-based call outcomes."""

from __future__ import annotations

import json
from pathlib import Path

from app.agent import detect_outcome


FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "outcome_eval.jsonl"


def evaluate(path: Path = FIXTURE) -> dict:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    failures = []
    for case in cases:
        actual = detect_outcome(case["text"])
        if actual != case["expected"]:
            failures.append({"id": case["id"], "expected": case["expected"], "actual": actual})
    return {
        "dataset": str(path),
        "total": len(cases),
        "correct": len(cases) - len(failures),
        "accuracy": round((len(cases) - len(failures)) / len(cases), 4) if cases else None,
        "failures": failures,
        "scope": "transcript outcome rules only; not STT, tools, or full voice-call accuracy",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
