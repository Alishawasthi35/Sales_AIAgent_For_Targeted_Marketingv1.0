# Sarvam Voice Sales Assistant

Startup-oriented implementation artifacts for a Sarvam-powered AI sales calling service.

This repository is organized around a low-to-medium budget pilot for targeted marketing calls:

- `docs/00-project-roadmap.md`: phased build, deployment, and testing roadmap.
- `docs/01-niche-and-offer.md`: first niche, ICP, positioning, offer, and success metrics.
- `docs/02-compliance-playbook.md`: consent, DNC, opt-out, calling windows, and risk controls.
- `docs/03-provider-selection.md`: Twilio-first decision with Telnyx cost-validation path.
- `docs/04-mvp-build-spec.md`: product, architecture, data model, call flow, and prompt scope.
- `docs/05-concierge-pilot-launch.md`: design-partner launch process and operating cadence.
- `docs/06-voice-cost-estimates-inr.md`: Twilio + Sarvam per-minute planning figures in INR.
- `tools/unit_economics.py`: editable cost calculator for pilot campaign economics.

The current implementation deliberately favors a concierge MVP: manual onboarding, tight campaign review, and a narrow appointment-booking use case before building broad self-serve functionality.

## Current MVP Slice

The first runnable slice implements the roadmap foundation:

- FastAPI backend with local SQLite storage.
- Client and campaign creation.
- CSV lead import with consent, source, phone, timezone, suppression, and campaign checks.
- Manual campaign and lead approval gates.
- Queueing only for approved campaigns and leads inside the local calling window.
- Twilio call creation dry-run support, status webhook storage, and Media Stream event logging.
- Realtime bidirectional voice bridge: Twilio inbound audio -> Sarvam streaming STT -> Sarvam LLM -> Sarvam streaming TTS -> Twilio outbound audio.
- Barge-in handling: Sarvam VAD speech-start events clear queued Twilio playback when the prospect interrupts.
- Appointment/callback CSV export endpoint.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy secrets\.env.example secrets\.env
```

Fill `secrets/.env` with real credentials when you are ready to test external APIs.

## Run Locally

```powershell
python scripts\bootstrap_demo.py
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API UI.

Useful demo flow:

```powershell
curl -F "file=@data/fixtures/solar_leads.csv" http://127.0.0.1:8000/campaigns/campaign_demo_solar/leads:upload
curl -X POST http://127.0.0.1:8000/campaigns/campaign_demo_solar/approve -H "Content-Type: application/json" -d "{\"approved_by\":\"founder\"}"
curl -X POST http://127.0.0.1:8000/campaigns/campaign_demo_solar/leads/approve
curl http://127.0.0.1:8000/campaigns/campaign_demo_solar/metrics
```

`POST /campaigns/{campaign_id}/dial-next` creates a dry-run call unless `PUBLIC_BASE_URL`, `TWILIO_FROM_NUMBER`, and Twilio credentials are configured.

## Agent Persona And Script

The live agent script comes from campaign fields:

- `agent_persona`: tone and behavior, for example "warm, concise solar appointment setter".
- `opening_script`: first line spoken when the call connects. Supports `{lead_name}`, `{product_interest}`, and `{client_name}`.
- `offer_summary`: what the call is about.
- `approved_claims` and `disallowed_claims`: guardrails for what the agent may say.
- `qualification_questions`: questions the agent should naturally cover.
- `objection_responses`: approved responses for price, busy, skeptical, or other objections.

The demo campaign in `scripts/bootstrap_demo.py` shows these fields.

## Realtime Call Test

1. Fill `secrets/.env` with Twilio and Sarvam keys.
2. Start a public HTTPS tunnel to your local server:

```powershell
ngrok http 8000
```

3. Set `PUBLIC_BASE_URL` in `secrets/.env` to the HTTPS ngrok URL and restart the server.
4. Seed and approve the demo campaign:

```powershell
python scripts\bootstrap_demo.py
python scripts\smoke_flow.py
curl -X POST http://127.0.0.1:8000/campaigns/campaign_demo_solar/queue
```

5. Start the next targeted call:

```powershell
curl -X POST http://127.0.0.1:8000/campaigns/campaign_demo_solar/dial-next
```

When the call connects, Twilio opens `/media/twilio/{call_id}`. The backend streams caller speech to Sarvam STT, generates a campaign-safe reply, streams Sarvam TTS back to Twilio as 8 kHz mulaw audio, and clears playback when the caller starts speaking.

## API Pings

```powershell
python scripts\api_ping.py --twilio
python scripts\api_ping.py --sarvam-llm
python tools\unit_economics.py --minutes 1000
```

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). For sensitive security reports, see [SECURITY.md](SECURITY.md).

## Push to GitHub

After cloning or `git init`, use your own repository URL:

```powershell
git add -A
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

Replace `YOUR_USER/YOUR_REPO` with your GitHub path. If the empty repo was created with default branch `main`, the `git branch -M main` step aligns a local `master` checkout with GitHub.
