from __future__ import annotations

import csv
import json
from contextlib import asynccontextmanager
from io import StringIO
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from twilio.rest import Client as TwilioClient

from app.compliance import is_inside_calling_window, normalize_phone, validate_lead_row
from app.config import settings
from app.db import connect, init_db, json_dump, row_to_dict, rows_to_dicts
from app.debug_log import debug_log
from app.main_helpers import audit, new_id, now_iso
from app.realtime import RealtimeCallBridge


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sarvam Voice Sales Assistant",
    description="Concierge MVP backend for consent-gated AI appointment-booking calls.",
    version="0.1.0",
    lifespan=lifespan,
)


class ClientCreate(BaseModel):
    name: str
    industry: str = ""
    billing_email: str = ""
    handoff_phone: str = ""
    timezone_default: str = Field(default_factory=lambda: settings.default_timezone)


class CampaignCreate(BaseModel):
    client_id: str
    name: str
    offer_summary: str = ""
    goal: str = "appointment_booking"
    approved_claims: list[str] = Field(default_factory=list)
    disallowed_claims: list[str] = Field(default_factory=list)
    ai_disclosure_mode: str = "conservative"
    recording_mode: str = "transcript_only"
    calling_window_start: str = "09:00"
    calling_window_end: str = "19:00"
    max_attempts: int = 3
    booking_link: str = ""
    agent_persona: str = "friendly, concise, consultative sales assistant"
    opening_script: str = ""
    qualification_questions: list[str] = Field(default_factory=list)
    objection_responses: dict[str, str] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved_by: str = "admin"


class SuppressionCreate(BaseModel):
    client_id: str
    phone_number: str
    reason: str = "manual_suppression"
    source_call_id: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": str(settings.database_path)}


@app.post("/clients")
def create_client(payload: ClientCreate) -> dict[str, Any]:
    client_id = new_id("client")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO clients
                (id, name, industry, billing_email, handoff_phone, timezone_default, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                payload.name,
                payload.industry,
                payload.billing_email,
                payload.handoff_phone,
                payload.timezone_default,
                now_iso(),
            ),
        )
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    audit("client.created", "client", client_id, payload.model_dump())
    return row_to_dict(row) or {}


@app.post("/campaigns")
def create_campaign(payload: CampaignCreate) -> dict[str, Any]:
    campaign_id = new_id("campaign")
    with connect() as conn:
        client = conn.execute("SELECT id FROM clients WHERE id = ?", (payload.client_id,)).fetchone()
        if client is None:
            raise HTTPException(status_code=404, detail="client_id not found")
        conn.execute(
            """
            INSERT INTO campaigns
                (
                    id, client_id, name, status, offer_summary, goal, approved_claims_json,
                    disallowed_claims_json, ai_disclosure_mode, recording_mode, calling_window_start,
                    calling_window_end, max_attempts, approval_status, booking_link, agent_persona,
                    opening_script, qualification_questions_json, objection_responses_json, created_at
                )
            VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                payload.client_id,
                payload.name,
                payload.offer_summary,
                payload.goal,
                json_dump(payload.approved_claims),
                json_dump(payload.disallowed_claims),
                payload.ai_disclosure_mode,
                payload.recording_mode,
                payload.calling_window_start,
                payload.calling_window_end,
                payload.max_attempts,
                payload.booking_link,
                payload.agent_persona,
                payload.opening_script,
                json_dump(payload.qualification_questions),
                json_dump(payload.objection_responses),
                now_iso(),
            ),
        )
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    audit("campaign.created", "campaign", campaign_id, payload.model_dump())
    return row_to_dict(row) or {}


@app.post("/campaigns/{campaign_id}/approve")
def approve_campaign(campaign_id: str, payload: ApprovalRequest) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="campaign not found")
        conn.execute(
            """
            UPDATE campaigns
            SET approval_status = 'approved', status = 'approved', approved_by = ?, approved_at = ?
            WHERE id = ?
            """,
            (payload.approved_by, now_iso(), campaign_id),
        )
        updated = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    audit("campaign.approved", "campaign", campaign_id, payload.model_dump(), actor_type="admin", actor_id=payload.approved_by)
    return row_to_dict(updated) or {}


@app.post("/campaigns/{campaign_id}/leads:upload")
async def upload_leads(campaign_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    raw = await file.read()
    reader = csv.DictReader(StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row")

    with connect() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if campaign is None:
            raise HTTPException(status_code=404, detail="campaign not found")

        suppressed_rows = conn.execute(
            "SELECT phone_e164 FROM suppression_entries WHERE client_id = ?",
            (campaign["client_id"],),
        ).fetchall()
        suppressed_numbers = {row["phone_e164"] for row in suppressed_rows}

        imported = 0
        ready = 0
        blocked = 0
        invalid = 0
        details: list[dict[str, Any]] = []

        for line_number, row in enumerate(reader, start=2):
            cleaned = {key: (value or "").strip() for key, value in row.items() if key is not None}
            result = validate_lead_row(cleaned, suppressed_numbers)

            if cleaned.get("client_id") and cleaned["client_id"] != campaign["client_id"]:
                result.errors.append("client_id does not match campaign")
            if cleaned.get("campaign_id") and cleaned["campaign_id"] != campaign_id:
                result.errors.append("campaign_id does not match upload path")

            compliance_error = any(
                marker in " ".join(result.errors)
                for marker in ("suppressed", "consent_status", "lead_source")
            )
            status = "ready_for_review" if result.passed else ("blocked_compliance" if compliance_error else "invalid")
            ready += int(status == "ready_for_review")
            blocked += int(status == "blocked_compliance")
            invalid += int(status == "invalid")

            lead_id = new_id("lead")
            conn.execute(
                """
                INSERT INTO leads
                    (
                        id, client_id, campaign_id, full_name, phone_number, phone_e164, timezone,
                        lead_source, source_record_id, consent_status, consent_timestamp,
                        consent_text_or_url, product_interest, notes, status,
                        validation_errors_json, created_at
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    campaign["client_id"],
                    campaign_id,
                    cleaned.get("full_name", ""),
                    cleaned.get("phone_number", ""),
                    result.phone_e164,
                    result.timezone,
                    cleaned.get("lead_source", ""),
                    cleaned.get("source_record_id", ""),
                    cleaned.get("consent_status", ""),
                    cleaned.get("consent_timestamp", ""),
                    cleaned.get("consent_text_or_url", ""),
                    cleaned.get("product_interest", ""),
                    cleaned.get("notes", ""),
                    status,
                    json_dump(result.errors),
                    now_iso(),
                ),
            )
            details.append({"line": line_number, "lead_id": lead_id, "status": status, "errors": result.errors})
            imported += 1

    audit(
        "leads.uploaded",
        "campaign",
        campaign_id,
        {"file_name": file.filename, "imported": imported, "ready_for_review": ready, "blocked_compliance": blocked, "invalid": invalid},
    )
    return {
        "campaign_id": campaign_id,
        "imported": imported,
        "ready_for_review": ready,
        "blocked_compliance": blocked,
        "invalid": invalid,
        "details": details,
    }


@app.post("/campaigns/{campaign_id}/leads/approve")
def approve_ready_leads(campaign_id: str) -> dict[str, Any]:
    with connect() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if campaign is None:
            raise HTTPException(status_code=404, detail="campaign not found")
        if campaign["approval_status"] != "approved":
            raise HTTPException(status_code=409, detail="campaign must be approved before leads can be approved for dialing")
        cursor = conn.execute(
            "UPDATE leads SET status = 'approved_for_dialing' WHERE campaign_id = ? AND status = 'ready_for_review'",
            (campaign_id,),
        )
    audit("leads.approved_for_dialing", "campaign", campaign_id, {"count": cursor.rowcount})
    return {"campaign_id": campaign_id, "approved_for_dialing": cursor.rowcount}


@app.post("/campaigns/{campaign_id}/queue")
def queue_campaign_leads(campaign_id: str) -> dict[str, Any]:
    with connect() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if campaign is None:
            raise HTTPException(status_code=404, detail="campaign not found")
        if campaign["approval_status"] != "approved":
            raise HTTPException(status_code=409, detail="campaign must be approved before queueing")

        leads = conn.execute(
            "SELECT * FROM leads WHERE campaign_id = ? AND status = 'approved_for_dialing'",
            (campaign_id,),
        ).fetchall()
        queued = 0
        blocked = 0
        for lead in leads:
            if is_inside_calling_window(lead["timezone"], campaign["calling_window_start"], campaign["calling_window_end"]):
                conn.execute("UPDATE leads SET status = 'queued' WHERE id = ?", (lead["id"],))
                queued += 1
            else:
                errors = json.loads(lead["validation_errors_json"] or "[]")
                errors.append("outside allowed local calling window")
                conn.execute(
                    "UPDATE leads SET status = 'blocked_compliance', validation_errors_json = ? WHERE id = ?",
                    (json_dump(errors), lead["id"]),
                )
                blocked += 1
    audit("leads.queued", "campaign", campaign_id, {"queued": queued, "blocked_compliance": blocked})
    return {"campaign_id": campaign_id, "queued": queued, "blocked_compliance": blocked}


@app.post("/suppression")
def create_suppression(payload: SuppressionCreate) -> dict[str, Any]:
    phone_e164 = normalize_phone(payload.phone_number)
    suppression_id = new_id("suppression")
    with connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO suppression_entries
                (id, client_id, phone_e164, reason, source_call_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (suppression_id, payload.client_id, phone_e164, payload.reason, payload.source_call_id, now_iso()),
        )
        conn.execute(
            "UPDATE leads SET status = 'suppressed', suppressed_at = ? WHERE client_id = ? AND phone_e164 = ?",
            (now_iso(), payload.client_id, phone_e164),
        )
        row = conn.execute(
            "SELECT * FROM suppression_entries WHERE client_id = ? AND phone_e164 = ?",
            (payload.client_id, phone_e164),
        ).fetchone()
    audit("suppression.created", "suppression", row["id"], {"phone_e164": phone_e164, "reason": payload.reason})
    return row_to_dict(row) or {}


@app.get("/campaigns/{campaign_id}/metrics")
def campaign_metrics(campaign_id: str) -> dict[str, Any]:
    with connect() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if campaign is None:
            raise HTTPException(status_code=404, detail="campaign not found")
        lead_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM leads WHERE campaign_id = ? GROUP BY status",
            (campaign_id,),
        ).fetchall()
        call_rows = conn.execute(
            "SELECT status, outcome, COUNT(*) AS count, COALESCE(SUM(cost_estimate_usd), 0) AS cost FROM calls WHERE campaign_id = ? GROUP BY status, outcome",
            (campaign_id,),
        ).fetchall()
    return {
        "campaign_id": campaign_id,
        "approval_status": campaign["approval_status"],
        "lead_statuses": {row["status"]: row["count"] for row in lead_rows},
        "calls": rows_to_dicts(call_rows),
    }


@app.post("/campaigns/{campaign_id}/dial-next")
def dial_next_lead(campaign_id: str) -> dict[str, Any]:
    with connect() as conn:
        campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if campaign is None:
            raise HTTPException(status_code=404, detail="campaign not found")
        lead = conn.execute(
            "SELECT * FROM leads WHERE campaign_id = ? AND status = 'queued' ORDER BY created_at LIMIT 1",
            (campaign_id,),
        ).fetchone()
        if lead is None:
            raise HTTPException(status_code=404, detail="no queued leads available")

        call_id = new_id("call")
        conn.execute(
            """
            INSERT INTO calls
                (id, client_id, campaign_id, lead_id, status, local_time_at_dial, created_at)
            VALUES (?, ?, ?, ?, 'created', ?, ?)
            """,
            (call_id, campaign["client_id"], campaign_id, lead["id"], now_iso(), now_iso()),
        )
        conn.execute(
            "UPDATE leads SET status = 'dialing', attempt_count = attempt_count + 1, last_attempt_at = ? WHERE id = ?",
            (now_iso(), lead["id"]),
        )

    if not settings.public_base_url or not settings.twilio_from_number:
        # region agent log
        debug_log(
            "live-call-setup",
            "H1",
            "app/main.py:dial_next_lead:dry_run",
            "Dial-next stayed in dry-run branch",
            {
                "campaign_id": campaign_id,
                "call_id": call_id,
                "lead_id": lead["id"],
                "has_public_base_url": bool(settings.public_base_url),
                "has_twilio_from_number": bool(settings.twilio_from_number),
            },
        )
        # endregion
        audit("call.dry_run_created", "call", call_id, {"lead_id": lead["id"]})
        return {"call_id": call_id, "lead_id": lead["id"], "dry_run": True, "reason": "PUBLIC_BASE_URL or TWILIO_FROM_NUMBER not configured"}

    twilio_sid = ""
    try:
        # region agent log
        debug_log(
            "live-call-setup",
            "H2",
            "app/main.py:dial_next_lead:twilio_create_attempt",
            "Attempting Twilio outbound call",
            {
                "campaign_id": campaign_id,
                "call_id": call_id,
                "lead_id": lead["id"],
                "has_to_number": bool(lead["phone_e164"]),
                "public_base_url_host": settings.public_base_url.split("//")[-1],
            },
        )
        # endregion
        client = TwilioClient()
        call = client.calls.create(
            to=lead["phone_e164"],
            from_=settings.twilio_from_number,
            url=f"{settings.public_base_url}/webhooks/twilio/answer?call_id={call_id}",
            status_callback=f"{settings.public_base_url}/webhooks/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        twilio_sid = call.sid
        with connect() as conn:
            conn.execute(
                "UPDATE calls SET provider_call_id = ?, status = 'dialing', started_at = ? WHERE id = ?",
                (twilio_sid, now_iso(), call_id),
            )
        audit("call.created", "call", call_id, {"provider_call_id": twilio_sid, "lead_id": lead["id"]})
        # region agent log
        debug_log(
            "live-call-setup",
            "H2",
            "app/main.py:dial_next_lead:twilio_create_success",
            "Twilio outbound call created",
            {"campaign_id": campaign_id, "call_id": call_id, "has_provider_call_id": bool(twilio_sid)},
        )
        # endregion
    except Exception as exc:
        # region agent log
        debug_log(
            "live-call-setup",
            "H2",
            "app/main.py:dial_next_lead:twilio_create_error",
            "Twilio outbound call creation failed",
            {"campaign_id": campaign_id, "call_id": call_id, "error_type": type(exc).__name__, "error": str(exc)[:300]},
        )
        # endregion
        with connect() as conn:
            conn.execute("UPDATE calls SET status = 'failed', outcome = ? WHERE id = ?", (str(exc), call_id))
        raise HTTPException(status_code=502, detail=f"Twilio call creation failed: {exc}") from exc

    return {"call_id": call_id, "lead_id": lead["id"], "provider_call_id": twilio_sid, "dry_run": False}


@app.post("/webhooks/twilio/answer")
def twilio_answer(call_id: str) -> Response:
    stream_url = ""
    if settings.public_base_url:
        stream_url = settings.public_base_url.replace("https://", "wss://").replace("http://", "ws://")

    # region agent log
    debug_log(
        "live-call-setup",
        "H3",
        "app/main.py:twilio_answer",
        "Twilio answer route generated TwiML",
        {"call_id": call_id, "has_stream_url": bool(stream_url), "public_base_url_host": settings.public_base_url.split("//")[-1]},
    )
    # endregion

    if stream_url:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}/media/twilio/{call_id}">
      <Parameter name="call_id" value="{call_id}" />
    </Stream>
  </Connect>
</Response>"""
    else:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Hi, this is a Sarvam Voice Sales Assistant test call.</Say>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.post("/webhooks/twilio/status")
async def twilio_status(request: Request) -> dict[str, str]:
    body = (await request.body()).decode()
    form = {key: values[-1] for key, values in parse_qs(body).items()}
    provider_call_id = form.get("CallSid", "")
    call_status = form.get("CallStatus", "unknown")
    duration = form.get("CallDuration")

    with connect() as conn:
        existing = conn.execute("SELECT * FROM calls WHERE provider_call_id = ?", (provider_call_id,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE calls
                SET status = ?, ended_at = CASE WHEN ? = 'completed' THEN ? ELSE ended_at END,
                    duration_seconds = COALESCE(?, duration_seconds), metadata_json = ?
                WHERE provider_call_id = ?
                """,
                (call_status, call_status, now_iso(), int(duration) if duration else None, json_dump(form), provider_call_id),
            )
    audit("twilio.status_webhook", "call", provider_call_id or "unknown", form)
    return {"status": "ok"}


@app.websocket("/media/twilio/{call_id}")
async def twilio_media(websocket: WebSocket, call_id: str) -> None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                calls.id AS call_id,
                campaigns.*,
                clients.name AS client_name
            FROM calls
            JOIN campaigns ON campaigns.id = calls.campaign_id
            JOIN clients ON clients.id = calls.client_id
            WHERE calls.id = ?
            """,
            (call_id,),
        ).fetchone()
        lead_row = conn.execute(
            """
            SELECT leads.*
            FROM calls
            JOIN leads ON leads.id = calls.lead_id
            WHERE calls.id = ?
            """,
            (call_id,),
        ).fetchone()

    if row is None or lead_row is None:
        await websocket.accept()
        # region agent log
        debug_log(
            "live-call-setup",
            "H3",
            "app/main.py:twilio_media:unknown_call",
            "Twilio media WebSocket arrived for unknown call",
            {"call_id": call_id, "has_call_row": row is not None, "has_lead_row": lead_row is not None},
        )
        # endregion
        await websocket.close(code=1008, reason="unknown call_id")
        return

    campaign = row_to_dict(row) or {}
    lead = row_to_dict(lead_row) or {}
    bridge = RealtimeCallBridge(websocket=websocket, call_id=call_id, campaign=campaign, lead=lead)
    await bridge.run()


@app.get("/exports/campaigns/{campaign_id}/appointments.csv")
def export_appointments(campaign_id: str) -> StreamingResponse:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT leads.full_name, leads.phone_e164, calls.outcome, calls.started_at, calls.ended_at, calls.metadata_json
            FROM calls
            LEFT JOIN leads ON leads.id = calls.lead_id
            WHERE calls.campaign_id = ? AND calls.outcome IN ('booked', 'callback_requested', 'qualified')
            ORDER BY calls.started_at DESC
            """,
            (campaign_id,),
        ).fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["full_name", "phone_e164", "outcome", "started_at", "ended_at", "metadata_json"])
    for row in rows:
        writer.writerow([row["full_name"], row["phone_e164"], row["outcome"], row["started_at"], row["ended_at"], row["metadata_json"]])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="campaign-{campaign_id}-appointments.csv"'},
    )

