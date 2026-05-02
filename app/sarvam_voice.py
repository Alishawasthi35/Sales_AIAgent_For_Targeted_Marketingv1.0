from __future__ import annotations

import asyncio
import base64
import wave
from io import BytesIO
from typing import Any

from sarvamai import AsyncSarvamAI

from app.audio import chunk_mulaw_base64, pcm16_to_mulaw_bytes
from app.config import settings


def sarvam_client() -> AsyncSarvamAI:
    if not settings.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY is required for live voice calls")
    return AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)


async def synthesize_twilio_mulaw_chunks(text: str) -> list[str]:
    client = sarvam_client()
    mulaw_audio = bytearray()

    async with client.text_to_speech_streaming.connect(
        model=settings.sarvam_tts_model,
        send_completion_event="true",
    ) as tts:
        await tts._send(
            {
                "type": "config",
                "data": {
                    "target_language_code": settings.sarvam_tts_language,
                    "speaker": settings.sarvam_tts_speaker,
                    "pace": settings.sarvam_tts_pace,
                    "speech_sample_rate": 8000,
                    "output_audio_codec": "mulaw",
                    "output_audio_bitrate": "32k",
                    "min_buffer_size": 20,
                    "max_chunk_length": 120,
                },
            }
        )
        await tts.convert(text)
        await tts.flush()

        while True:
            message = await asyncio.wait_for(tts.recv(), timeout=30)
            message_type = getattr(message, "type", None)
            if message_type == "audio":
                data = getattr(message, "data", None)
                if data is not None:
                    mulaw_audio.extend(_audio_output_to_mulaw(data))
            elif message_type == "event":
                event_data = getattr(message, "data", None)
                if getattr(event_data, "event_type", None) == "final":
                    break
            elif message_type == "error":
                raise RuntimeError(f"Sarvam TTS error: {message}")

    return chunk_mulaw_base64(bytes(mulaw_audio))


def extract_stt_message(message: Any) -> tuple[str, str]:
    message_type = getattr(message, "type", "")
    data = getattr(message, "data", None)
    if message_type == "events" and data is not None:
        signal = getattr(data, "signal_type", "") or getattr(data, "event_type", "")
        if signal == "START_SPEECH":
            return "speech_start", ""
        if signal == "END_SPEECH":
            return "speech_end", ""
    if message_type == "data" and data is not None:
        transcript = getattr(data, "transcript", "")
        if transcript:
            return "transcript", transcript
    if message_type == "error":
        return "error", str(message)
    return "", ""


def _audio_output_to_mulaw(data: Any) -> bytes:
    content_type = (getattr(data, "content_type", "") or "").lower()
    raw = base64.b64decode(getattr(data, "audio", ""))

    if "mulaw" in content_type or "mu-law" in content_type or content_type in {"audio/basic", "audio/mulaw"}:
        return raw
    if "wav" in content_type:
        return _wav_bytes_to_mulaw(raw)
    if "linear16" in content_type or "pcm" in content_type:
        return pcm16_to_mulaw_bytes(raw)

    # Sarvam's streaming config requests mulaw. If the content type is generic,
    # assume the bytes are already the requested codec rather than adding headers.
    return raw


def _wav_bytes_to_mulaw(raw: bytes) -> bytes:
    with wave.open(BytesIO(raw), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
        sample_width = wav.getsampwidth()
        channels = wav.getnchannels()
    if sample_width != 2:
        raise RuntimeError("Only 16-bit WAV TTS output can be bridged to Twilio")
    if channels > 1:
        frames = _downmix_pcm16_to_mono(frames, channels)
    return pcm16_to_mulaw_bytes(frames)


def _downmix_pcm16_to_mono(frames: bytes, channels: int) -> bytes:
    import struct

    values = struct.iter_unpack("<" + "h" * channels, frames[: len(frames) - (len(frames) % (2 * channels))])
    mono = bytearray()
    for sample_group in values:
        averaged = int(sum(sample_group) / channels)
        mono.extend(struct.pack("<h", averaged))
    return bytes(mono)

