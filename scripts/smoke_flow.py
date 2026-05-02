from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from scripts.bootstrap_demo import CAMPAIGN_ID, main as bootstrap_demo  # noqa: E402


def main() -> None:
    bootstrap_demo()
    client = TestClient(app)

    health = client.get("/health")
    health.raise_for_status()

    fixture_bytes = _live_test_fixture_bytes()
    upload = client.post(
        f"/campaigns/{CAMPAIGN_ID}/leads:upload",
        files={"file": ("solar_leads.csv", fixture_bytes, "text/csv")},
    )
    upload.raise_for_status()

    approval = client.post(f"/campaigns/{CAMPAIGN_ID}/approve", json={"approved_by": "smoke"})
    approval.raise_for_status()

    lead_approval = client.post(f"/campaigns/{CAMPAIGN_ID}/leads/approve")
    lead_approval.raise_for_status()

    metrics = client.get(f"/campaigns/{CAMPAIGN_ID}/metrics")
    metrics.raise_for_status()

    print("Smoke flow passed")
    print(metrics.json())


def _live_test_fixture_bytes() -> bytes:
    fixture = ROOT / "data" / "fixtures" / "solar_leads.csv"
    rows = fixture.read_text(encoding="utf-8").splitlines()
    if len(rows) < 2 or not settings.twilio_to_number:
        return fixture.read_bytes()

    header = rows[0].split(",")
    first = rows[1].split(",")
    replacements = {
        "full_name": "Live Test Lead",
        "phone_number": settings.twilio_to_number,
        "phone_e164": "",
        "lead_source": "test_fixture",
        "source_record_id": "live_test_verified_number",
        "timezone_or_region": settings.default_timezone,
        "notes": "Uses TWILIO_TO_NUMBER so Twilio trial accounts can place the live test call",
    }
    for column, value in replacements.items():
        if column in header:
            first[header.index(column)] = value
    rows[1] = ",".join(first)
    return ("\n".join(rows) + "\n").encode("utf-8")


if __name__ == "__main__":
    main()

