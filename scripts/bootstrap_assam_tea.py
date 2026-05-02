from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, init_db, json_dump  # noqa: E402
from app.main import now_iso  # noqa: E402

CLIENT_ID = "client_assam_agro_tea"
CAMPAIGN_ID = "campaign_assam_agro_tea_retail"


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
                "Assam Agro Tea",
                "beverages",
                "hello@assamagrotea.example",
                "+918000123456",
                "Asia/Kolkata",
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
                "Assam Agro Tea — retail sampler and reorder calls",
                "draft",
                (
                    "Introduce Assam Agro Tea: premium orthodox and CTC blends from Assam, "
                    "offer a short taste-kit or retail partner callback, and book follow-ups for bulk or café orders."
                ),
                "appointment_booking",
                json_dump(
                    [
                        "Tea is sourced from Assam partner gardens with traceable batches.",
                        "We offer sample packs and wholesale sheets for verified retailers.",
                        "You can request a callback from our trade desk for pricing tiers.",
                    ]
                ),
                json_dump(
                    [
                        "Medical or curative health claims about tea.",
                        "Guaranteed revenue or shelf turnover for stockists.",
                        "Claims we are the only authentic Assam tea in the market.",
                    ]
                ),
                "conservative",
                "transcript_only",
                "10:00",
                "18:00",
                3,
                "pending",
                "https://calendar.example/assam-agro-tea",
                (
                    "Warm, knowledgeable tea brand ambassador for Assam Agro Tea; concise, respectful of busy shop owners; "
                    "uses simple product language without jargon."
                ),
                (
                    "Hi {lead_name}, this is an AI assistant calling on behalf of {client_name} about "
                    "{product_interest}. Is now a quick moment to chat?"
                ),
                json_dump(
                    [
                        "Do you currently stock specialty or single-origin teas?",
                        "Are you exploring Assam orthodox, CTC, or both for your customers?",
                        "Would a sample kit or a short trade-desk callback be more useful?",
                    ]
                ),
                json_dump(
                    {
                        "price": (
                            "Retail and wholesale rates depend on volume and blend. "
                            "I can note your interest and have trade desk share the right sheet."
                        ),
                        "busy": "No problem. What day or time works for a quick callback?",
                        "skeptical": (
                            "Totally fair. I can keep this to one minute: we only want to see if a sample or "
                            "trade sheet is useful—no obligation."
                        ),
                    }
                ),
                now_iso(),
            ),
        )

    template = ROOT / "data" / "fixtures" / "assam_tea_leads.csv"
    print(f"Seeded client={CLIENT_ID} campaign={CAMPAIGN_ID} (Assam Agro Tea)")
    print(f"Import sample leads with: curl -F file=@{template} http://127.0.0.1:8000/campaigns/{CAMPAIGN_ID}/leads:upload")


if __name__ == "__main__":
    main()
