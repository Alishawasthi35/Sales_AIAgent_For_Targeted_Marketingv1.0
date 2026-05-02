from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


def require_sarvam_key() -> str:
    if not settings.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY is not set in secrets/.env")
    return settings.sarvam_api_key


def ping_sarvam_llm() -> None:
    api_key = require_sarvam_key()
    started = time.perf_counter()
    response = httpx.post(
        f"{settings.sarvam_base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "api-subscription-key": api_key},
        json={
            "model": "sarvam-m",
            "messages": [{"role": "user", "content": "Reply with one short sentence confirming the API works."}],
        },
        timeout=30,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    print(f"Sarvam LLM status={response.status_code} latency_ms={elapsed_ms}")
    if response.is_error:
        print(response.text[:1000])
        response.raise_for_status()
    print(response.text[:1000])


def ping_twilio_identity() -> None:
    from twilio.rest import Client

    started = time.perf_counter()
    client = Client()
    account = client.api.accounts(client.username).fetch()
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    print(f"Twilio account status={account.status} sid={account.sid} latency_ms={elapsed_ms}")


def main() -> None:
    parser = argparse.ArgumentParser(description="API ping checks for Twilio and Sarvam.")
    parser.add_argument("--twilio", action="store_true", help="Ping Twilio account identity.")
    parser.add_argument("--sarvam-llm", action="store_true", help="Ping Sarvam chat completion endpoint.")
    args = parser.parse_args()

    if not args.twilio and not args.sarvam_llm:
        parser.error("Choose at least one ping: --twilio or --sarvam-llm")

    if args.twilio:
        ping_twilio_identity()
    if args.sarvam_llm:
        ping_sarvam_llm()


if __name__ == "__main__":
    main()

