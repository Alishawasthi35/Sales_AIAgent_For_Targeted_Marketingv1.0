from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
SECRETS_ENV = ROOT_DIR / "secrets" / ".env"
LOCAL_ENV = ROOT_DIR / ".env"

load_dotenv(SECRETS_ENV)
load_dotenv(LOCAL_ENV)


@dataclass(frozen=True)
class Settings:
    database_path: Path = ROOT_DIR / "data" / "app.db"
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")
    twilio_to_number: str = os.getenv("TWILIO_TO_NUMBER", "")
    default_phone_region: str = os.getenv("DEFAULT_PHONE_REGION", "US")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "America/New_York")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    sarvam_base_url: str = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")
    sarvam_chat_model: str = os.getenv("SARVAM_CHAT_MODEL", "sarvam-30b")
    sarvam_stt_model: str = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
    sarvam_stt_language: str = os.getenv("SARVAM_STT_LANGUAGE", "en-IN")
    sarvam_stt_mode: str = os.getenv("SARVAM_STT_MODE", "transcribe")
    sarvam_tts_model: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
    sarvam_tts_language: str = os.getenv("SARVAM_TTS_LANGUAGE", "en-IN")
    sarvam_tts_speaker: str = os.getenv("SARVAM_TTS_SPEAKER", "priya")
    sarvam_tts_pace: float = float(os.getenv("SARVAM_TTS_PACE", "1.05"))
    max_agent_turn_words: int = int(os.getenv("MAX_AGENT_TURN_WORDS", "38"))


settings = Settings()

