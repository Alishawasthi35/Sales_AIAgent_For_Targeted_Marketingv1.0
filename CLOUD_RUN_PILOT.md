# Google Cloud pilot: safe first deployment

This repo now supports a **synthetic, no-call Cloud Run pilot**. The existing Sarvam/Twilio voice agent remains the main project. The pilot adds a container, protected admin routes, signed Twilio webhook checks, streaming TTS, structured operational events, and offline evaluation.

## Why live calling is blocked on Cloud Run today

The application stores leads, consent, opt-outs, calls, and transcripts in SQLite. Cloud Run's local filesystem is temporary and each instance has its own copy. Losing or splitting the opt-out list could cause an unwanted call. The application therefore refuses to start on Cloud Run unless `ALLOW_EPHEMERAL_DEMO=true`, and it refuses to start with `ENABLE_LIVE_CALLS=true`. Do not upload real leads to the demo.

Before a live pilot, move the database to a durable shared store (Cloud SQL PostgreSQL is a reasonable choice), migrate the schema and queries, verify opt-outs across instances/restarts, and run a consent-reviewed test call. The webhook signature checks and API token are additional safeguards, not substitutes for persistence.

## First-time Google Cloud setup

1. Sign in at [Google Cloud Console](https://console.cloud.google.com/). Review and accept the Google Cloud terms yourself. Choose **India** only if it matches your account and billing details.
2. Create a new project, for example `sarvam-voice-pilot`. Note its **project ID** (different from the display name).
3. Link a billing account if Google Cloud asks. A payment method or free-trial enrollment must be completed by the account owner. Set a small monthly budget with email alerts before deploying. **Budget alerts are notifications, not a guaranteed spending cap.**
4. Enable **Cloud Run**, **Cloud Build**, **Artifact Registry**, and **Secret Manager** APIs. The console may prompt for these during deployment.
5. Create a random, unique `ADMIN_API_TOKEN` in Secret Manager. Do not put it in Git or chat. Grant the Cloud Run runtime service account access to this secret only. No Sarvam or Twilio key is needed for the no-call demo.
6. Deploy this repository to Cloud Run in a region near you, such as `asia-south1`, using source deployment. The `Dockerfile` is used automatically. Configure `ALLOW_EPHEMERAL_DEMO=true`, `ENABLE_LIVE_CALLS=false`, `DATABASE_PATH=/tmp/sarvam-agent.db`, and the `ADMIN_API_TOKEN` secret. Set **minimum instances 0**, **maximum instances 1**, and a request timeout appropriate for a short demo. Cloud Run must allow unauthenticated *platform* access for Twilio webhooks in a future live deployment; the app requires its own admin token and validates Twilio signatures. Restrict access to the demo if public access is unnecessary.
7. Open the service URL plus `/health`. It should return `{"status":"ok"}`. Other API routes require `Authorization: Bearer <ADMIN_API_TOKEN>`. Never paste that token into a URL, repository, screenshot, or chat.

The demo should use synthetic records only. It cannot place calls; `/campaigns/{id}/dial-next` returns 503 on Cloud Run. When Cloud Run creates multiple instances or restarts, local SQLite data can disappear. A green health check demonstrates packaging and startup, not live voice reliability.

## Local checks without provider accounts

```powershell
python -m pip install -r requirements.txt pytest
python -m pytest -q
python -m tools.evaluate_outcomes
```

The outcome fixture contains 32 synthetic transcript snippets. It checks the current rule-based classification only. It does not measure speech recognition, LLM quality, tool calls, or real call quality.

## Operational measurements

During a future consent-reviewed voice pilot, stdout JSON events appear in Cloud Logging. Export events as JSONL, then run:

```powershell
python tools/analyze_telemetry.py events.jsonl --cost-usd 0.42
```

The cost argument must be the **actual combined** Google Cloud, Twilio, and Sarvam cost for those exact calls, from their billing records. The summary reports:

- `speech_end_to_first_audio_sent_ms_p50/p95`: a server-side proxy for response latency, not the caller's perceived end-to-end latency. Add synchronized client/provider timestamps for true end-to-end latency.
- `interruption_clear_rate`: share of detected speech interruptions for which a Twilio `clear` was sent, not a measured perceptual interruption success rate. Validate with recorded, consented test calls.
- `call_error_rate`: completed calls with provider or turn errors divided by completed calls.
- `actual_cost_usd_per_minute`: invoice cost divided by completed call minutes. Missing invoices produce `null`.
- `tool_call_accuracy`: `null`, because this agent currently has no external tool-calling workflow. Add one and an annotated evaluation set before reporting this metric.

Do not put audio, transcripts, names, phone numbers, or credentials into operational logs. The existing application audit/database records can contain personal data, so only use synthetic data in this demo.

## Next engineering gate for live calls

1. Replace SQLite with a shared durable database and test suppression after instance replacement and concurrent calls.
2. Add durable, access-controlled storage for any transcripts retained, with an explicit retention period.
3. Restore working Sarvam and Twilio accounts. Store keys in Secret Manager. Verify Twilio HTTP and WebSocket signatures on the public URL, including URL/proxy behavior.
4. Use test numbers and consenting participants. Measure at least 20 varied calls, including interruptions, silence, opt-outs, provider failures, and language variation. Review audio manually before publishing latency or accuracy claims.
5. Reconcile usage records from all three vendors against the same call IDs to compute cost per minute.
