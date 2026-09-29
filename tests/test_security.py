import asyncio
from dataclasses import replace

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from twilio.request_validator import RequestValidator

from app import security


def make_request(signature):
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "path": "/webhooks/twilio/status",
        "query_string": b"",
        "headers": [(b"x-twilio-signature", signature.encode())],
        "server": ("localhost", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b"CallSid=CA123", "more_body": False}

    return Request(scope, receive)


def test_cloud_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(
        security,
        "settings",
        replace(security.settings, cloud_run=True, twilio_auth_token="test-token", public_base_url="https://agent.example"),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(security.validate_twilio_http(make_request("invalid")))
    assert error.value.status_code == 403


def test_cloud_webhook_accepts_valid_signature(monkeypatch):
    monkeypatch.setattr(
        security,
        "settings",
        replace(security.settings, cloud_run=True, twilio_auth_token="test-token", public_base_url="https://agent.example"),
    )
    url = "https://agent.example/webhooks/twilio/status"
    signature = RequestValidator("test-token").compute_signature(url, {"CallSid": "CA123"})
    asyncio.run(security.validate_twilio_http(make_request(signature)))


def test_cloud_admin_token_required(monkeypatch):
    monkeypatch.setattr(
        security,
        "settings",
        replace(security.settings, cloud_run=True, admin_api_token="private-token"),
    )
    assert not security.admin_authorized(None)
    assert not security.admin_authorized("Bearer wrong-token")
    assert security.admin_authorized("Bearer private-token")
