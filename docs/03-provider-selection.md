# Calling Provider Selection

## Decision

Prototype with Twilio first, then run a Telnyx validation spike before paid scale.

Rationale:

- Twilio is already present in the workspace via `make_call.py`.
- Twilio has clear US outbound pricing, Media Streams pricing, and mature programmable voice documentation.
- The first milestone is proving the call loop and sales behavior, not minimizing every cent.
- Telnyx appears cheaper for scaled voice AI workloads, so it should be evaluated before moving beyond the concierge MVP.

## Provider Roles

The calling provider should handle:

- Outbound dialing.
- Caller ID and phone number management.
- PSTN connection.
- Realtime media streaming over WebSocket.
- Call status webhooks.
- Answering machine detection.
- Recording if enabled.
- Transfer to a human closer.

The application should handle:

- Campaign approval and lead eligibility.
- Call state.
- Sarvam STT/LLM/TTS orchestration.
- Script policy and guardrails.
- Compliance logging.
- Outcome classification.
- Client reporting.

## Twilio-First Prototype

Use Twilio for the first working prototype because it reduces integration risk.

Prototype goals:

- Place an outbound call from the backend.
- Stream call audio to a WebSocket endpoint.
- Send caller audio to Sarvam STT.
- Generate a response using Sarvam LLM.
- Convert response to voice with Sarvam TTS.
- Return audio into the call.
- Store call metadata, transcript, and outcome.

Recommended Twilio features:

- Programmable Voice outbound calls.
- Media Streams for WebSocket audio.
- Answering Machine Detection for campaigns where voicemail handling matters.
- Call status webhooks for lifecycle events.
- Call recording only after recording policy is approved.

Avoid initially:

- Branded Calling, because $0.12/call can dominate pilot cost.
- ConversationRelay, because $0.07/minute is convenient but expensive for a custom Sarvam stack.
- Complex SIP/BYOC setup unless a client already has a carrier contract.

## Telnyx Validation Spike

Run a separate cost and quality spike once Twilio proves the agent behavior.

Validation goals:

- Confirm destination-specific outbound price for target geographies.
- Confirm WebSocket media streaming behavior and audio formats.
- Compare call answer rate and call quality against Twilio.
- Compare answering machine detection accuracy.
- Confirm support experience and debugging tools.
- Confirm whether phone-number reputation and throughput fit outbound marketing use.

Acceptance criteria:

- Telnyx produces similar or better call quality.
- End-to-end latency is not worse than Twilio by more than 250 ms.
- Campaign-level variable cost is at least 15-25% lower after all fees.
- Developer workflow does not materially slow down support.

If Telnyx passes, add a provider abstraction before scaling. If it does not, keep Twilio until volume discounts or BYOC become relevant.

## Provider Abstraction

Do not overbuild provider abstraction on day one. Create a narrow interface around the operations that are likely to differ.

Suggested interface:

```python
class CallingProvider:
    def create_call(self, lead, campaign) -> str:
        ...

    def transfer_call(self, call_id: str, destination: str) -> None:
        ...

    def stop_call(self, call_id: str) -> None:
        ...

    def parse_status_webhook(self, payload) -> dict:
        ...

    def parse_media_event(self, payload) -> dict:
        ...
```

Start with a Twilio implementation and keep Telnyx notes in the spike document. Add a real second implementation only when the business has enough call volume to justify it.

## Cost Comparison Assumptions

Twilio US reference costs:

- Outbound call: $0.014/minute.
- Media Streams: $0.004/minute.
- Local number: about $1.15/month.
- Answering machine detection: $0.0075/call.
- Recording: $0.0025/minute.

Telnyx reference costs:

- Voice API: $0.002/minute plus SIP trunking destination fee.
- Media streaming: $0.0035/minute.
- Answering machine detection: $0.002/call.
- Recording: $0.002/minute.

Sarvam AI costs are independent of telephony provider, so provider choice mostly changes telephony, streaming, AMD, recording, and number costs.

## Operational Decision Matrix

Use Twilio if:

- The goal is fastest prototype.
- The team wants the most common docs and examples.
- Early client margin can absorb the extra per-minute cost.
- Debuggability and support are more important than carrier optimization.

Use Telnyx if:

- The call volume grows beyond pilot scale.
- Per-minute margin becomes a constraint.
- WebSocket behavior and call quality pass validation.
- The team is comfortable with a slightly more infrastructure-oriented telephony stack.

Use BYOC/SIP later if:

- Clients already have carrier contracts.
- Volumes exceed 100k minutes/month.
- Carrier reputation, STIR/SHAKEN, and branded calling become major conversion levers.

## Implementation Path

Phase 1:

- Keep `make_call.py` as the minimal Twilio smoke test.
- Add a backend route that returns TwiML with a Media Stream connection.
- Add a WebSocket endpoint for stream events.
- Log incoming audio events and call lifecycle events.

Phase 2:

- Connect the stream to Sarvam STT.
- Add response generation and TTS.
- Implement opt-out and transfer flows.

Phase 3:

- Run 50-100 internal test calls.
- Measure latency, transcript quality, interruption handling, voicemail behavior, and per-call cost.

Phase 4:

- Re-run the same tests on Telnyx.
- Decide whether to keep Twilio, switch to Telnyx, or support both.

## Decision

The MVP should be Twilio-first for speed and reliability, with a mandatory Telnyx cost-quality spike before scaling past paid pilots.
