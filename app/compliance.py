from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import phonenumbers

from app.config import settings


APPROVED_LEAD_SOURCES = {
    "inbound_form",
    "ad_lead",
    "existing_customer",
    "prior_inquiry",
    "event_signup",
    "webinar_signup",
    "demo_signup",
    "referral_with_consent",
    "test_fixture",
}

CONSENT_STATUSES = {"explicit", "consented", "opted_in", "yes", "true", "1"}

REQUIRED_LEAD_FIELDS = {
    "full_name",
    "phone_number",
    "lead_source",
    "consent_status",
    "consent_timestamp",
    "consent_text_or_url",
    "timezone_or_region",
    "client_id",
    "campaign_id",
}

TIMEZONE_ALIASES = {
    "eastern": "America/New_York",
    "central": "America/Chicago",
    "mountain": "America/Denver",
    "pacific": "America/Los_Angeles",
    "india": "Asia/Kolkata",
    "ist": "Asia/Kolkata",
}


@dataclass
class LeadValidationResult:
    phone_e164: str = ""
    timezone: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def normalize_phone(phone_number: str) -> str:
    parsed = phonenumbers.parse(phone_number, None if phone_number.startswith("+") else settings.default_phone_region)
    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        raise ValueError("phone_number is not a valid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_timezone(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("timezone_or_region is required")
    candidate = TIMEZONE_ALIASES.get(candidate.lower(), candidate)
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"timezone_or_region is not a known timezone: {candidate}") from exc
    return candidate


def parse_hhmm(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def is_inside_calling_window(timezone_name: str, window_start: str, window_end: str) -> bool:
    local_now = datetime.now(ZoneInfo(timezone_name)).time()
    start = parse_hhmm(window_start)
    end = parse_hhmm(window_end)
    return start <= local_now <= end


def validate_lead_row(row: dict[str, str], suppressed_numbers: set[str]) -> LeadValidationResult:
    result = LeadValidationResult()

    missing = sorted(field for field in REQUIRED_LEAD_FIELDS if not (row.get(field) or "").strip())
    result.errors.extend(f"missing required field: {field}" for field in missing)

    if row.get("phone_number"):
        try:
            result.phone_e164 = normalize_phone(row["phone_number"].strip())
        except ValueError as exc:
            result.errors.append(str(exc))

    if row.get("timezone_or_region"):
        try:
            result.timezone = normalize_timezone(row["timezone_or_region"].strip())
        except ValueError as exc:
            result.errors.append(str(exc))

    lead_source = (row.get("lead_source") or "").strip()
    if lead_source and lead_source not in APPROVED_LEAD_SOURCES:
        result.errors.append(f"lead_source is not approved for MVP: {lead_source}")

    consent_status = (row.get("consent_status") or "").strip().lower()
    if consent_status and consent_status not in CONSENT_STATUSES:
        result.errors.append(f"consent_status is not dialable: {row.get('consent_status')}")

    if result.phone_e164 and result.phone_e164 in suppressed_numbers:
        result.errors.append("phone number is suppressed for this client")

    return result

