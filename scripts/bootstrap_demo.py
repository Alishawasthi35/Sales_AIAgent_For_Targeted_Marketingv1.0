from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, init_db, json_dump  # noqa: E402
from app.main import now_iso  # noqa: E402


CLIENT_ID = "client_demo_solar"
CAMPAIGN_ID = "campaign_demo_solar"


def main() -> None:
    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM calls WHERE campaign_id = ?", (CAMPAIGN_ID,))
        conn.execute("DELETE FROM leads WHERE campaign_id = ?", (CAMPAIGN_ID,))
        conn.execute("DELETE FROM suppression_entries WHERE client_id = ?", (CLIENT_ID,))
        conn.execute(
            """
            INSERT OR IGNORE INTO clients
                (id, name, industry, billing_email, handoff_phone, timezone_default, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                CLIENT_ID,
                "GreenPeak Solar",
                "solar",
                "ops@greenpeak.example",
                "+14155550199",
                "America/Los_Angeles",
                now_iso(),
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO campaigns
                (
                    id, client_id, name, status, offer_summary, goal, approved_claims_json,
                    disallowed_claims_json, ai_disclosure_mode, recording_mode,
                    calling_window_start, calling_window_end, max_attempts,
                    approval_status, booking_link, agent_persona, opening_script,
                    qualification_questions_json, objection_responses_json, created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                CAMPAIGN_ID,
                CLIENT_ID,
                "Solar consultation booking",
                "draft",
                "Book a free solar savings consultation for recent inbound quote requests.",
                "appointment_booking",
                json_dump(["Free consultation", "No obligation quote review", "Licensed local installation partners"]),
                json_dump(["Guaranteed savings", "Government rebate eligibility without review"]),
                "conservative",
                "transcript_only",
                "09:00",
                "19:00",
                3,
                "pending",
                "https://calendar.example/greenpeak",
                "warm, professional solar appointment setter who sounds calm and helpful",
                "Hi {lead_name}, this is an AI assistant calling on behalf of GreenPeak Solar about your recent solar quote request. Is now a good time for a quick follow-up?",
                json_dump([
                    "Are you the homeowner?",
                    "Are you mainly interested in lowering the bill, backup power, or both?",
                    "Would you like a specialist to review options with you?",
                ]),
                json_dump(
                    {
                        "price": "The exact price depends on roof, usage, and plan. A short review is the right next step.",
                        "busy": "No problem, I can mark a better callback time.",
                        "skeptical": "That is fair. I can keep this brief and only help schedule a human review if useful.",
                    }
                ),
                now_iso(),
            ),
        )

    template = ROOT / "data" / "fixtures" / "solar_leads.csv"
    print(f"Seeded demo client={CLIENT_ID} campaign={CAMPAIGN_ID}")
    print(f"Import sample leads with: curl -F file=@{template} http://127.0.0.1:8000/campaigns/{CAMPAIGN_ID}/leads:upload")


if __name__ == "__main__":
    main()

