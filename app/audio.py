from __future__ import annotations

import base64
import struct


BIAS = 0x84
CLIP = 32635


def mulaw_bytes_to_pcm16(mulaw: bytes) -> bytes:
    samples = bytearray()
    for value in mulaw:
        decoded = _mulaw_decode_sample(value)
        samples.extend(struct.pack("<h", decoded))
    return bytes(samples)


def pcm16_to_mulaw_bytes(pcm16: bytes) -> bytes:
    samples = struct.iter_unpack("<h", pcm16[: len(pcm16) - (len(pcm16) % 2)])
    return bytes(_mulaw_encode_sample(sample[0]) for sample in samples)


def twilio_payload_to_pcm16(payload: str) -> bytes:
    return mulaw_bytes_to_pcm16(base64.b64decode(payload))


def pcm16_to_base64(pcm16: bytes) -> str:
    return base64.b64encode(pcm16).decode("ascii")


def chunk_mulaw_base64(mulaw_audio: bytes, frame_size: int = 160) -> list[str]:
    return [
        base64.b64encode(mulaw_audio[index : index + frame_size]).decode("ascii")
        for index in range(0, len(mulaw_audio), frame_size)
        if mulaw_audio[index : index + frame_size]
    ]


def _mulaw_decode_sample(value: int) -> int:
    value = ~value & 0xFF
    sign = value & 0x80
    exponent = (value >> 4) & 0x07
    mantissa = value & 0x0F
    sample = ((mantissa << 3) + BIAS) << exponent
    sample -= BIAS
    return -sample if sign else sample


def _mulaw_encode_sample(sample: int) -> int:
    sign = 0x80 if sample < 0 else 0
    if sample < 0:
        sample = -sample
    sample = min(sample, CLIP) + BIAS

    exponent = 7
    mask = 0x4000
    while exponent > 0 and not (sample & mask):
        mask >>= 1
        exponent -= 1

    mantissa = (sample >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF

