from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sarvamai import AsyncSarvamAI

from app.config import settings


OPT_OUT_PHRASES = (
    "do not call",
    "don't call",
    "remove me",
    "stop calling",
    "take me off",
    "unsubscribe",
    "not contact me again",
)

CALLBACK_PHRASES = ("call me later", "callback", "call back", "busy", "later")
BOOKING_PHRASES = ("book", "schedule", "appointment", "meeting", "consultation")
NOT_INTERESTED_PHRASES = ("not interested", "no thanks", "don't need", "do not need")
BAD_NUMBER_PHRASES = ("wrong number", "who is this", "not me")


@dataclass
class ConversationState:
    campaign: dict[str, Any]
    lead: dict[str, Any]
    turns: list[dict[str, str]] = field(default_factory=list)
    outcome: str | None = None
    risk_flags: list[str] = field(default_factory=list)

    def add_turn(self, speaker: str, text: str) -> None:
        self.turns.append({"role": speaker, "content": text})
        self.turns = self.turns[-10:]


def opening_line(campaign: dict[str, Any], lead: dict[str, Any]) -> str:
    configured = (campaign.get("opening_script") or "").strip()
    if configured:
        return configured.format(
            lead_name=lead.get("full_name", "there"),
            product_interest=lead.get("product_interest", ""),
            client_name=campaign.get("client_name", "the business"),
        )
    return (
        f"Hi {lead.get('full_name') or 'there'}, this is an AI assistant calling about "
        f"{campaign.get('offer_summary') or 'your recent inquiry'}. Is now a good time for a quick follow-up?"
    )


def detect_outcome(text: str) -> str | None:
    lowered = text.lower()
    if any(phrase in lowered for phrase in OPT_OUT_PHRASES):
        return "opted_out"
    if any(phrase in lowered for phrase in BAD_NUMBER_PHRASES):
        return "bad_number"
    if any(phrase in lowered for phrase in CALLBACK_PHRASES):
        return "callback_requested"
    if any(phrase in lowered for phrase in BOOKING_PHRASES):
        return "qualified"
    if any(phrase in lowered for phrase in NOT_INTERESTED_PHRASES):
        return "not_interested"
    return None


def build_system_prompt(campaign: dict[str, Any], lead: dict[str, Any]) -> str:
    approved_claims = _load_json(campaign.get("approved_claims_json"), [])
    disallowed_claims = _load_json(campaign.get("disallowed_claims_json"), [])
    questions = _load_json(campaign.get("qualification_questions_json"), [])
    objections = _load_json(campaign.get("objection_responses_json"), {})

    return f"""
You are a live AI voice sales assistant. Persona: {campaign.get("agent_persona")}.

Call goal: {campaign.get("goal")}.
Offer: {campaign.get("offer_summary")}.
Lead: {lead.get("full_name")} interested in {lead.get("product_interest")}.
Lead source: {lead.get("lead_source")}. Notes: {lead.get("notes")}.
Booking link or handoff: {campaign.get("booking_link")}.

Rules:
- Say you are an AI assistant if asked or if the opening script discloses it.
- Keep each spoken reply under {settings.max_agent_turn_words} words.
- Ask one question at a time.
- Use only approved claims: {approved_claims}.
- Never make these disallowed claims: {disallowed_claims}.
- Qualification questions to cover naturally: {questions}.
- Objection responses: {objections}.
- If the prospect asks not to be called, apologize, say you will mark do-not-call, and end.
- If wrong number, apologize and end.
- If interested, move toward booking or callback.
- Do not ask for sensitive personal data or payment details.
""".strip()


async def generate_agent_reply(state: ConversationState, user_text: str) -> tuple[str, str | None]:
    outcome = detect_outcome(user_text)
    if outcome == "opted_out":
        return "Understood. I will mark you as do-not-call. Sorry for the interruption.", outcome
    if outcome == "bad_number":
        return "Sorry about that. I will mark this as a wrong number and end the call.", outcome
    if outcome == "not_interested":
        return "No problem. Thanks for your time, and I will not continue the sales conversation.", outcome

    state.add_turn("user", user_text)

    if not settings.sarvam_api_key:
        reply = _fallback_reply(state, user_text)
        state.add_turn("assistant", reply)
        return reply, outcome

    client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
    messages = [{"role": "system", "content": build_system_prompt(state.campaign, state.lead)}]
    messages.extend(state.turns)
    response = await client.chat.completions(
        model=settings.sarvam_chat_model,
        messages=messages,
        temperature=0.35,
        max_tokens=120,
    )
    reply = _extract_chat_text(response) or _fallback_reply(state, user_text)
    reply = _shorten_for_voice(reply)
    state.add_turn("assistant", reply)
    return reply, outcome


def _fallback_reply(state: ConversationState, user_text: str) -> str:
    lowered = user_text.lower()
    if "price" in lowered or "cost" in lowered:
        return "Good question. Pricing depends on your needs, so the best next step is a quick consultation. Would you like to schedule one?"
    if "ai" in lowered or "robot" in lowered:
        return "Yes, I am an AI assistant calling on behalf of the business to help with quick follow-up and booking."
    if "yes" in lowered or "interested" in lowered:
        return "Great. I can help arrange a short consultation. What day or time generally works best for you?"
    return "Thanks. May I ask one quick question to see if this is a good fit for you?"


def _extract_chat_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "") if message else ""
    if isinstance(content, str):
        return content
    return str(content or "")


def _shorten_for_voice(text: str) -> str:
    words = text.strip().split()
    if len(words) <= settings.max_agent_turn_words:
        return text.strip()
    return " ".join(words[: settings.max_agent_turn_words]).rstrip(".,;:") + "."


def _load_json(value: Any, default: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default

