"""Authentication for public webhook endpoints and private admin operations."""

from __future__ import annotations

import hmac
from urllib.parse import parse_qs

from fastapi import HTTPException, Request, WebSocket
from twilio.request_validator import RequestValidator

from app.config import settings


def admin_authorized(header: str | None) -> bool:
    if not settings.admin_api_token:
        return not settings.cloud_run
    prefix = "Bearer "
    if not header or not header.startswith(prefix):
        return False
    return hmac.compare_digest(header[len(prefix) :], settings.admin_api_token)


async def validate_twilio_http(request: Request) -> None:
    if not settings.twilio_auth_token and not settings.cloud_run:
        return
    if not settings.twilio_auth_token or not settings.public_base_url:
        raise HTTPException(status_code=503, detail="Twilio verification is not configured")
    signature = request.headers.get("x-twilio-signature", "")
    body = (await request.body()).decode("utf-8")
    form = {key: values[-1] for key, values in parse_qs(body).items()}
    url = settings.public_base_url + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    if not RequestValidator(settings.twilio_auth_token).validate(url, form, signature):
        raise HTTPException(status_code=403, detail="invalid Twilio signature")


def twilio_websocket_authorized(websocket: WebSocket) -> bool:
    if not settings.twilio_auth_token and not settings.cloud_run:
        return True
    if not settings.twilio_auth_token or not settings.public_base_url:
        return False
    signature = websocket.headers.get("x-twilio-signature", "")
    url = settings.public_base_url.replace("https://", "wss://") + websocket.url.path
    if websocket.url.query:
        url += "?" + websocket.url.query
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, {}, signature) or validator.validate(url + "/", {}, signature)
