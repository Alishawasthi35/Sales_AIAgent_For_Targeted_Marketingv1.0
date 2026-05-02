# Step-by-Step Project Roadmap

This roadmap is the execution plan for building the Sarvam Voice Sales Assistant from the current Twilio smoke-test project into a validated concierge MVP. It is based on the complete project scope captured in the business plan, compliance playbook, provider decision, MVP build spec, pilot launch kit, and unit-economics calculator.

The product is not a generic robocaller. It is a consent-aware AI lead-response and appointment-booking system for warm leads. The first commercial use case is high-value local services, such as solar, roofing, HVAC, renovation, real estate inquiry follow-up, or education counseling.

## Scope Summary

The MVP should prove that an AI assistant can call consent-backed leads, introduce the client, understand the prospect, qualify interest, handle simple objections, book or request a callback, record the outcome, and stop immediately when a prospect opts out.

Core components:

- Twilio-first outbound calling and media streaming.
- Sarvam STT, LLM, and TTS for the AI call loop.
- Lead import with consent metadata.
- Compliance gate before dialing.
- Campaign queue and retry rules.
- Call transcript and outcome storage.
- Unit-economics tracking.
- Human test validation before client pilots.
- Concierge-operated first client launch.

Out of scope for the first version:

- Scraped phone-number collection.
- Purchased cold-list dialing.
- Fully autonomous lead generation.
- Predictive dialer behavior.
- Complex CRM marketplace integrations.
- Enterprise analytics.
- Regulated verticals without legal review.

## Phase 1: Project Foundation and API Ping Validation

Objective: prove that the environment, credentials, and external APIs work independently before building any orchestration.

### Build Steps

1. Confirm local project structure:
   - `make_call.py` remains the Twilio outbound smoke test.
   - `secrets/.env.example` remains the credential template.
   - `secrets/.env` holds local secrets and stays ignored.
   - `tools/unit_economics.py` remains the cost model.
   - `docs/` remains the planning and operating source of truth.

2. Define required environment variables:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_FROM_NUMBER`
   - `TWILIO_TO_NUMBER`
   - `SARVAM_API_KEY`
   - Future: `PUBLIC_BASE_URL` for webhook callbacks.

3. Prepare local test fixtures:
   - One fake client.
   - One fake campaign.
   - 10 fake leads using consenting test numbers only.
   - One approved script.
   - One opt-out test scenario.
   - One callback-request test scenario.

4. Define the first three demo campaigns:
   - Solar consultation booking.
   - Real estate inquiry follow-up.
   - Education/course counseling callback.

### Deployment Steps

1. Run everything locally first.
2. Use only verified/test phone numbers.
3. Do not expose public endpoints until local pings work.
4. After local pings pass, deploy a minimal webhook server to a low-cost host or tunnel local development through a temporary HTTPS URL.

### API Ping Testing Cycle

Twilio checks:

1. Load Twilio credentials from `secrets/.env`.
2. Call Twilio account/API identity endpoint or create a harmless outbound test call.
3. Run `make_call.py` to place one call to a verified test number.
4. Confirm the call SID is printed.
5. Confirm the Twilio console shows the call attempt.
6. Confirm invalid credentials fail with a clear error.

Sarvam checks:

1. Load `SARVAM_API_KEY`.
2. Send a one-sentence text prompt to the Sarvam LLM.
3. Send one short text phrase to Sarvam TTS and verify playable audio is returned.
4. Send a short local audio sample to Sarvam STT and verify transcript output.
5. Log response time and failure messages for each request.

Cost checks:

1. Run `python tools/unit_economics.py`.
2. Run a 1,000-minute scenario.
3. Run a 5,000-minute scenario.
4. Record expected platform cost per connected minute.

### Human Testing Cycle

Use only founder/team numbers in this phase.

1. Run 5 Twilio test calls.
2. Confirm caller ID is correct.
3. Confirm the opening audio is audible.
4. Confirm missed call, busy, and failed call states are visible.
5. Confirm there is no use of real client leads.

### Exit Criteria

- Twilio outbound call succeeds.
- Sarvam LLM ping succeeds.
- Sarvam TTS ping succeeds.
- Sarvam STT ping succeeds.
- Unit-economics calculator runs.
- Required environment variables are documented.
- No credentials are written into source files.
- The team understands true API failure behavior before building the call loop.

### Deliverables

- Working API ping checklist.
- Fake campaign fixture.
- Fake lead CSV format.
- Baseline cost estimate.
- Decision to proceed to compliance-gated lead intake.

## Phase 2: Lead Intake, Consent Storage, and Compliance Gate

Objective: ensure the system only dials phone numbers that are valid, consent-backed, unsuppressed, and attached to an approved campaign.

### Build Steps

1. Define the lead CSV schema:
   - `full_name`
   - `phone_number`
   - `phone_e164`
   - `lead_source`
   - `source_record_id`
   - `consent_status`
   - `consent_timestamp`
   - `consent_text_or_url`
   - `timezone_or_region`
   - `client_id`
   - `campaign_id`
   - `product_interest`
   - `notes`

2. Add or specify a lead-import process:
   - Read CSV rows.
   - Validate required fields.
   - Normalize phone numbers to E.164.
   - Reject invalid phone numbers.
   - Reject missing consent.
   - Reject unknown lead sources.
   - Reject numbers already suppressed.

3. Define lead statuses:
   - `uploaded`
   - `invalid`
   - `blocked_compliance`
   - `ready_for_review`
   - `approved_for_dialing`
   - `queued`
   - `dialing`
   - `completed`
   - `suppressed`

4. Define campaign approval fields:
   - campaign goal.
   - approved claims.
   - disallowed claims.
   - calling window.
   - max attempts.
   - AI disclosure mode.
   - recording mode.
   - handoff phone or booking link.
   - approval status.

5. Define suppression behavior:
   - Normalize all suppression numbers to E.164.
   - Match suppression by phone number.
   - Block suppressed leads before queueing.
   - Store opt-out source call ID when available.

### Deployment Steps

1. Start with local CSV validation.
2. Add a simple local database or structured storage only after schema is stable.
3. Keep campaign approval manual.
4. Do not connect this phase to auto-dialing until validation tests pass.

### Testing Cycle

Positive tests:

1. Upload a valid CSV with 10 fake leads.
2. Confirm all valid rows become `ready_for_review`.
3. Approve a test campaign.
4. Confirm valid leads can move to `approved_for_dialing`.

Negative tests:

1. Upload a row without phone number.
2. Upload a row with invalid phone format.
3. Upload a row without consent timestamp.
4. Upload a row without lead source.
5. Upload a row with a suppressed number.
6. Upload a row outside the allowed timezone/calling-window logic.
7. Confirm each invalid row is blocked with a reason.

Compliance tests:

1. Simulate "do not call" and write a suppression entry.
2. Re-upload the same number.
3. Confirm the number is blocked.
4. Confirm campaign cannot dial before approval.
5. Confirm audit logs capture upload, validation, approval, and suppression events.

### Human Testing Cycle

1. Ask 2-3 testers to inspect fake lead rows.
2. Confirm the lead source and consent fields are understandable.
3. Confirm the intended opening line matches the lead source.
4. Confirm no tester believes the system is using random numbers.

### Exit Criteria

- Invalid leads cannot be dialed.
- Unknown-source leads cannot be dialed.
- Suppressed numbers cannot be dialed.
- Campaigns cannot dial before approval.
- Local calling-window logic is defined.
- Every blocked lead has a clear reason.
- The first demo campaign has a clean lead list.

### Deliverables

- Final lead CSV template.
- Compliance validation checklist.
- Suppression-list behavior.
- Campaign approval checklist.
- Ready-to-dial fake campaign.

## Phase 3: Twilio and Sarvam Realtime Call Loop

Objective: build the first end-to-end AI phone conversation loop using Twilio for calling and Sarvam for STT, LLM, and TTS.

### Build Steps

1. Twilio call control:
   - Create outbound call.
   - Return TwiML for call behavior.
   - Receive call status webhooks.
   - Store provider call ID.

2. Media streaming:
   - Add Twilio Media Streams WebSocket endpoint.
   - Receive start, media, mark, and stop events.
   - Decode or transform audio as required.
   - Log stream session IDs.

3. Sarvam STT:
   - Send caller audio chunks or buffered test audio to Sarvam STT.
   - Capture partial/final transcripts where supported.
   - Store transcript turns.

4. Agent runtime:
   - Build prompt from campaign, lead, approved claims, and conversation state.
   - Keep responses short for phone calls.
   - Prevent unapproved claims.
   - Detect transfer, callback, not interested, wrong number, and opt-out intent.

5. Sarvam TTS:
   - Convert agent response text to audio.
   - Return or play the audio through the call path.
   - Track TTS latency.

6. Call state:
   - Track states such as `dialing`, `connected`, `qualifying`, `callback_requested`, `booked`, `not_interested`, `opted_out`, `failed`, and `completed`.
   - Store outcome and cost estimate.

### Deployment Steps

1. Run locally with a public HTTPS tunnel for Twilio webhooks.
2. Test with one verified phone number.
3. Deploy a minimal backend once WebSocket behavior is stable.
4. Add logging before adding more testers.
5. Keep all campaigns fake in this phase.

### API Ping and Integration Testing Cycle

Pre-call pings:

1. Ping Twilio credentials.
2. Ping Sarvam LLM.
3. Ping Sarvam TTS.
4. Ping Sarvam STT with a known audio sample.
5. Confirm webhook URL is reachable.
6. Confirm WebSocket endpoint accepts connection.

Call-loop tests:

1. Place one call with static TwiML audio.
2. Place one call with Media Streams connected but no AI response.
3. Place one call with STT-only logging.
4. Place one call with STT + LLM text logging.
5. Place one call with STT + LLM + TTS response.
6. Place one call with opt-out phrase.
7. Place one call with callback request.
8. Place one call with wrong-number response.

Latency tests:

1. Measure Twilio connection setup time.
2. Measure STT response time.
3. Measure LLM first-response time.
4. Measure TTS generation time.
5. Measure perceived delay after the tester stops speaking.

### Human Testing Cycle

Run 20-30 internal calls:

1. 5 normal interested-lead calls.
2. 5 callback-request calls.
3. 5 objection-handling calls.
4. 5 interruption/barge-in calls.
5. 5 opt-out/wrong-number calls.
6. Optional: 5 noisy or slow-speech calls.

Score each call:

- Opening clarity.
- Speech recognition correctness.
- Intent understanding.
- Response relevance.
- Naturalness.
- Latency.
- Correct final outcome.
- Compliance behavior.

### Exit Criteria

- End-to-end call loop works with a real human.
- Opt-out calls create suppression entries.
- Wrong-number calls do not continue selling.
- Callback and appointment outcomes are captured.
- Average perceived response delay is usually below 2 seconds.
- No severe hallucinated or unapproved claims in internal tests.
- Logs are good enough to debug failed calls.

### Deliverables

- Working Twilio/Sarvam call-loop prototype.
- Internal call transcript samples.
- Latency baseline.
- Failure-mode list.
- Decision on fixes before broader human validation.

## Phase 4: Structured Human Product Validation

Objective: generate credible validation numbers, recordings, transcripts, and cost data before approaching paying clients.

### Build Steps

1. Create a human testing sheet with columns:
   - `test_call_id`
   - `tester_name`
   - `phone_number`
   - `scenario`
   - `call_connected`
   - `opening_clear`
   - `intent_understood`
   - `expected_outcome`
   - `actual_outcome`
   - `outcome_correct`
   - `opt_out_expected`
   - `opt_out_handled`
   - `latency_rating_1_to_5`
   - `naturalness_rating_1_to_5`
   - `call_duration_seconds`
   - `estimated_cost_usd`
   - `notes`

2. Prepare tester scenarios:
   - Interested lead wants appointment.
   - Busy lead asks for callback.
   - Price objection.
   - Skeptical lead asks if it is AI.
   - Wrong number.
   - Angry opt-out.
   - Lead asks out-of-scope question.
   - Lead interrupts repeatedly.
   - Lead pauses for a long time.

3. Prepare demo campaign assets:
   - Solar consultation script.
   - Real estate inquiry script.
   - Education counseling script.
   - Five objections per campaign.
   - Expected outcome map per scenario.

4. Prepare validation report template:
   - Number of attempted calls.
   - Number of connected calls.
   - Outcome accuracy.
   - Opt-out accuracy.
   - Average duration.
   - Average cost.
   - Human naturalness rating.
   - Known limitations.
   - Next pilot proposal.

### Deployment Steps

1. Keep calling limited to opted-in testers.
2. Run calls in small batches of 5-10.
3. Review transcripts after every batch.
4. Fix prompt, TTS wording, or state handling before the next batch.
5. Do not approach clients until evidence targets are met.

### Testing Cycle

Run 50 attempted test calls:

1. 10 solar campaign calls.
2. 10 real estate campaign calls.
3. 10 education campaign calls.
4. 10 objection-heavy calls.
5. 10 opt-out, wrong-number, callback, and interruption calls.

Review after each batch:

1. Did the agent correctly understand the prospect?
2. Did the agent classify the outcome correctly?
3. Did it stop when asked?
4. Did it make any unapproved claims?
5. Was latency acceptable?
6. Was the voice understandable?
7. Did the call produce a useful transcript and summary?

### Evidence Targets

Minimum before client outreach:

- 50 attempted test calls.
- 35+ connected calls.
- 80%+ correct outcome classification.
- 90%+ opt-out detection in opt-out tests.
- 0 severe compliance failures.
- Fewer than 2 unapproved-claim incidents per 50 calls.
- 3.5/5 or higher average naturalness rating.
- Most calls have perceived response delay below 2 seconds.
- Estimated platform cost around $0.04-$0.08 per connected minute, subject to real billing.

### Client Outreach Assets

Prepare:

- 1-page validation report.
- 2-3 anonymized call recordings.
- 3-5 anonymized transcripts.
- Demo campaign summary.
- Unit-economics output.
- Compliance posture summary.
- 7-14 day pilot offer.

Client-facing proof statement:

```text
We ran 50 controlled human test calls across 3 appointment-booking scenarios.
The assistant correctly classified outcomes in X% of connected calls, detected opt-outs in Y% of opt-out tests, and operated at an estimated platform cost of $A-$B per connected minute.
We are looking for 2-3 design partners with consent-backed warm leads for a controlled pilot.
```

### Exit Criteria

- Validation report is ready.
- Demo recordings and transcripts are presentable.
- Known failure modes have mitigations.
- The team can explain exactly where lead phone numbers come from.
- The team can explain why the system is consent-aware.
- The pitch is based on observed data, not assumptions.

### Deliverables

- Human validation report.
- Demo call pack.
- Updated scripts and prompts.
- Product limitations list.
- Go/no-go decision for client pilots.

## Phase 5: Concierge Client Pilot and Production Hardening

Objective: test business value with 1-3 real design partners while keeping operations controlled, compliant, and manually reviewed.

### Build Steps

1. Client onboarding:
   - Capture business name, offer, service area, sales hours, handoff number, booking link, and current lead sources.
   - Confirm the client has at least 100 warm leads per month.
   - Confirm their current cost per booked appointment.

2. Lead onboarding:
   - Import 25-100 warm leads for the first micro-pilot.
   - Verify lead source and consent samples.
   - Scrub against client suppression list.
   - Approve only dialable leads.

3. Campaign setup:
   - Create one campaign goal.
   - Approve opening line.
   - Approve qualification questions.
   - Approve objections.
   - Approve disallowed claims.
   - Approve AI disclosure mode.
   - Approve recording mode.
   - Approve retry schedule.

4. Operations:
   - Cap calls at 10-20 per day in week one.
   - Review every connected-call transcript during soft launch.
   - Pause campaigns on risk triggers.
   - Send weekly reports.

5. Product hardening:
   - Add dashboard/export for booked appointments.
   - Add QA review status.
   - Add cost-per-campaign reporting.
   - Add retry and voicemail rules.
   - Add Telnyx comparison only after Twilio pilot is stable.

### Deployment Steps

1. Deploy backend to a stable low-cost host.
2. Configure public HTTPS webhook URLs.
3. Configure Twilio status callbacks.
4. Configure Twilio Media Streams endpoint.
5. Set environment variables securely.
6. Run API ping checks after deployment.
7. Run one internal test call on deployed infrastructure.
8. Run one client-approved test call before live dialing.
9. Start with 10 live leads.
10. Expand only if first calls pass quality review.

### Production API Ping Checks

Before each live calling day:

1. Twilio credential check.
2. Twilio outbound call capability check.
3. Webhook reachability check.
4. Media WebSocket reachability check.
5. Sarvam STT ping.
6. Sarvam LLM ping.
7. Sarvam TTS ping.
8. Database write check.
9. Suppression-list read/write check.
10. Unit-cost estimate check.

### Client Pilot Testing Cycle

Micro-pilot:

1. Dial 10 leads.
2. Review every transcript.
3. Check opt-outs, complaints, wrong numbers, latency, and unapproved claims.
4. Fix script or prompt before dialing more.

Controlled pilot:

1. Dial 25-100 leads over 7-14 days.
2. Keep daily call caps.
3. Send daily internal review notes.
4. Send weekly client summary.
5. Compare booked appointments with client baseline.

Scale test:

1. Expand to 300-1,000 leads only after clean micro-pilot.
2. Sample at least 20% of connected-call transcripts.
3. Monitor campaign economics.
4. Pause if risk thresholds are crossed.

### Success Metrics

Business:

- 8-12% of connected conversations produce booked appointment or qualified callback.
- Cost per booked appointment beats or approaches the client's current channel.
- Gross margin stays above 60%.
- Client wants to continue after pilot.

Compliance:

- Opt-out rate below 5%.
- Complaint rate below 0.5%.
- No unknown-source leads dialed.
- No suppressed numbers dialed.
- No severe unapproved claims.

Product:

- Average perceived latency mostly below 2 seconds.
- Outcome classification above 80%.
- Transcripts useful for review.
- Human handoff or callback capture works.
- Daily operations are manageable.

### Exit Criteria

- At least one client pilot completes cleanly.
- Client confirms appointment quality is useful.
- Cost and margin are understood.
- Operational workload is measured.
- Top automation needs are obvious.
- Decision is made: continue Twilio, test Telnyx, or pause for product fixes.

### Deliverables

- Client pilot report.
- Cost-per-campaign report.
- Transcript quality review.
- Compliance incident log.
- Product backlog for next version.
- Provider optimization decision.

## Master Deployment Gates

Do not advance unless the current gate is satisfied:

1. API Gate: Twilio and Sarvam ping checks pass independently.
2. Compliance Gate: invalid, unknown-source, or suppressed leads cannot be dialed.
3. Call-Loop Gate: realtime human call works end-to-end.
4. Validation Gate: 50-call human test evidence is strong enough for outreach.
5. Client Gate: first client pilot shows useful outcomes, clean compliance, and positive gross margin.

## Immediate Execution Order

1. Confirm `secrets/.env` has Twilio credentials and add Sarvam key when available.
2. Run Twilio outbound smoke test with `make_call.py`.
3. Create Sarvam API ping scripts or checks.
4. Create fake lead CSVs for the three demo campaigns.
5. Build or document CSV validation and compliance gating.
6. Add Twilio webhook and Media Streams endpoints.
7. Connect Sarvam STT, LLM, and TTS.
8. Run 20-30 internal call-loop tests.
9. Run 50 structured human validation calls.
10. Prepare demo recordings, transcripts, and validation report.
11. Approach 2-3 design partners for a 7-14 day controlled pilot.
