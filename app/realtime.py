from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.agent import ConversationState, generate_agent_reply, opening_line
from app.audio import pcm16_to_base64, twilio_payload_to_pcm16
from app.config import settings
from app.db import connect, json_dump
from app.debug_log import debug_log
from app.main_helpers import audit, new_id, now_iso
from app.sarvam_voice import extract_stt_message, sarvam_client, stream_twilio_mulaw_chunks
from app.telemetry import emit, monotonic_ms


class RealtimeCallBridge:
    def __init__(self, websocket: WebSocket, call_id: str, campaign: dict[str, Any], lead: dict[str, Any]):
        self.websocket = websocket
        self.call_id = call_id
        self.stream_sid = ""
        self.state = ConversationState(campaign=campaign, lead=lead)
        self.audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=200)
        self.stop_event = asyncio.Event()
        self.media_events = 0
        self.started_ms = monotonic_ms()
        self.last_speech_end_ms: int | None = None
        self.reply_task: asyncio.Task[None] | None = None
        self.send_lock = asyncio.Lock()
        self.playback_pending = False
        self.active_playback_mark: str | None = None
        self.turn_count = 0
        self.interruption_attempts = 0
        self.interruption_clears = 0
        self.provider_errors = 0

    async def run(self) -> None:
        await self.websocket.accept()
        emit("call.connected", self.call_id)
        audit("realtime.connected", "call", self.call_id, {"lead_id": self.state.lead.get("id")})
        # region agent log
        debug_log(
            "live-call-setup",
            "H3",
            "app/realtime.py:run",
            "Realtime bridge accepted WebSocket",
            {
                "call_id": self.call_id,
                "has_sarvam_key": bool(settings.sarvam_api_key),
                "campaign_id": self.state.campaign.get("id"),
                "lead_id": self.state.lead.get("id"),
            },
        )
        # endregion

        if not settings.sarvam_api_key:
            await self.websocket.close(code=1011, reason="SARVAM_API_KEY is required")
            return

        stt_task = asyncio.create_task(self._run_stt_loop())
        twilio_task = asyncio.create_task(self._receive_twilio_loop())
        try:
            done, _ = await asyncio.wait({stt_task, twilio_task}, return_when=asyncio.FIRST_COMPLETED)
            if stt_task in done and twilio_task not in done:
                self.provider_errors += 1
                emit("provider.error", self.call_id, provider="sarvam_stt", error_type="stream_ended")
                await self.websocket.close(code=1011, reason="speech service unavailable")
            for task in done:
                if task.cancelled():
                    continue
                error = task.exception()
                if error:
                    raise error
        finally:
            self.stop_event.set()
            await self._cancel_reply()
            stt_task.cancel()
            twilio_task.cancel()
            await asyncio.gather(stt_task, twilio_task, return_exceptions=True)
            self._persist_media_count()
            emit(
                "call.finished",
                self.call_id,
                duration_ms=monotonic_ms() - self.started_ms,
                turns=self.turn_count,
                media_events=self.media_events,
                interruption_attempts=self.interruption_attempts,
                interruption_clears=self.interruption_clears,
                provider_errors=self.provider_errors,
            )

    async def _receive_twilio_loop(self) -> None:
        try:
            while True:
                payload = await self.websocket.receive_json()
                event = payload.get("event", "unknown")
                if event == "start":
                    start = payload.get("start", {})
                    self.stream_sid = start.get("streamSid") or payload.get("streamSid", "")
                    audit("twilio.media.start", "call", self.call_id, payload)
                    # region agent log
                    debug_log(
                        "live-call-setup",
                        "H3",
                        "app/realtime.py:_receive_twilio_loop:start",
                        "Twilio media stream started",
                        {
                            "call_id": self.call_id,
                            "has_stream_sid": bool(self.stream_sid),
                            "tracks": start.get("tracks", []),
                            "media_format": start.get("mediaFormat", {}),
                        },
                    )
                    # endregion
                    self.reply_task = asyncio.create_task(
                        self._speak(opening_line(self.state.campaign, self.state.lead), mark_name="opening")
                    )
                elif event == "media":
                    self.media_events += 1
                    media_payload = payload.get("media", {}).get("payload", "")
                    if media_payload:
                        await self._queue_audio(twilio_payload_to_pcm16(media_payload))
                elif event == "mark":
                    if payload.get("mark", {}).get("name") == self.active_playback_mark:
                        self.playback_pending = False
                        self.active_playback_mark = None
                    audit("twilio.media.mark", "call", self.call_id, payload)
                elif event == "dtmf":
                    audit("twilio.media.dtmf", "call", self.call_id, payload)
                elif event == "stop":
                    audit("twilio.media.stop", "call", self.call_id, payload)
                    break
        except WebSocketDisconnect:
            audit("twilio.media.disconnect", "call", self.call_id, {"media_events": self.media_events})

    async def _run_stt_loop(self) -> None:
        client = sarvam_client()
        # region agent log
        debug_log(
            "live-call-setup",
            "H4",
            "app/realtime.py:_run_stt_loop",
            "Connecting to Sarvam streaming STT",
            {
                "call_id": self.call_id,
                "model": settings.sarvam_stt_model,
                "language": settings.sarvam_stt_language,
                "mode": settings.sarvam_stt_mode,
            },
        )
        # endregion
        async with client.speech_to_text_streaming.connect(
            model=settings.sarvam_stt_model,
            mode=settings.sarvam_stt_mode,
            language_code=settings.sarvam_stt_language,
            sample_rate="8000",
            input_audio_codec="pcm_s16le",
            high_vad_sensitivity="true",
            vad_signals="true",
            flush_signal="true",
        ) as stt:
            sender = asyncio.create_task(self._send_audio_to_stt(stt))
            receiver = asyncio.create_task(self._receive_stt_messages(stt))
            try:
                done, _ = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    if task.cancelled():
                        continue
                    error = task.exception()
                    if error:
                        raise error
            finally:
                sender.cancel()
                receiver.cancel()
                await asyncio.gather(sender, receiver, return_exceptions=True)

    async def _send_audio_to_stt(self, stt: Any) -> None:
        while not self.stop_event.is_set():
            pcm16 = await self.audio_queue.get()
            if pcm16 is None:
                break
            await stt.transcribe(audio=pcm16_to_base64(pcm16), encoding="pcm_s16le", sample_rate=8000)

    async def _receive_stt_messages(self, stt: Any) -> None:
        while not self.stop_event.is_set():
            message = await stt.recv()
            event, text = extract_stt_message(message)
            if event == "speech_start":
                if self.reply_task and not self.reply_task.done():
                    self.interruption_attempts += 1
                    emit("interruption.detected", self.call_id, turn=self.turn_count)
                    await self._cancel_reply()
                if self.playback_pending:
                    await self._clear_playback()
            elif event == "speech_end":
                self.last_speech_end_ms = monotonic_ms()
            elif event == "transcript" and text.strip():
                await self._cancel_reply()
                self.reply_task = asyncio.create_task(self._handle_transcript(text.strip()))
            elif event == "error":
                self.provider_errors += 1
                emit("provider.error", self.call_id, provider="sarvam_stt")
                audit("sarvam.stt.error", "call", self.call_id, {"error": text})

    async def _handle_transcript(self, text: str) -> None:
        self.turn_count += 1
        turn = self.turn_count
        transcript_ms = monotonic_ms()
        stt_after_speech_ms = (
            transcript_ms - self.last_speech_end_ms if self.last_speech_end_ms is not None else None
        )
        speech_end_ms = self.last_speech_end_ms
        self.last_speech_end_ms = None
        # region agent log
        debug_log(
            "live-call-setup",
            "H4",
            "app/realtime.py:_handle_transcript",
            "Received transcript from Sarvam STT",
            {"call_id": self.call_id, "transcript_length": len(text)},
        )
        # endregion
        try:
            self._store_turn("user", text)
            llm_start_ms = monotonic_ms()
            reply, outcome = await generate_agent_reply(self.state, text)
            llm_ms = monotonic_ms() - llm_start_ms
            if outcome:
                self.state.outcome = outcome
                self._update_outcome(outcome)
            self._store_turn("assistant", reply)
            await self._speak(
                reply,
                mark_name=f"turn-{turn}",
                turn=turn,
                speech_end_ms=speech_end_ms,
                stt_after_speech_ms=stt_after_speech_ms,
                llm_ms=llm_ms,
                outcome=outcome,
            )
        except asyncio.CancelledError:
            emit("turn.cancelled", self.call_id, turn=turn)
            raise
        except Exception as exc:
            self.provider_errors += 1
            emit("turn.error", self.call_id, turn=turn, error_type=type(exc).__name__)
            raise

    async def _speak(
        self,
        text: str,
        mark_name: str,
        turn: int = 0,
        speech_end_ms: int | None = None,
        stt_after_speech_ms: int | None = None,
        llm_ms: int | None = None,
        outcome: str | None = None,
    ) -> None:
        if not self.stream_sid:
            return
        tts_start_ms = monotonic_ms()
        first_audio_ms: int | None = None
        chunk_count = 0
        async for payload in stream_twilio_mulaw_chunks(text):
            if first_audio_ms is None:
                first_audio_ms = monotonic_ms()
            await self._send_twilio(
                {"event": "media", "streamSid": self.stream_sid, "media": {"payload": payload}}
            )
            self.playback_pending = True
            self.active_playback_mark = mark_name
            chunk_count += 1
        # region agent log
        debug_log(
            "live-call-setup",
            "H5",
            "app/realtime.py:_speak",
            "Sending synthesized TTS audio to Twilio",
            {"call_id": self.call_id, "text_length": len(text), "chunk_count": chunk_count, "mark_name": mark_name},
        )
        # endregion
        await self._send_twilio(
            {"event": "mark", "streamSid": self.stream_sid, "mark": {"name": mark_name}}
        )
        emit(
            "turn.audio_sent" if turn else "opening.audio_sent",
            self.call_id,
            turn=turn,
            stt_after_speech_ms=stt_after_speech_ms,
            llm_ms=llm_ms,
            tts_first_chunk_ms=first_audio_ms - tts_start_ms if first_audio_ms is not None else None,
            speech_to_first_audio_sent_ms=(
                first_audio_ms - speech_end_ms
                if first_audio_ms is not None and speech_end_ms is not None
                else None
            ),
            audio_chunks=chunk_count,
            outcome=outcome,
        )

    async def _clear_playback(self) -> None:
        if self.stream_sid:
            await self._send_twilio({"event": "clear", "streamSid": self.stream_sid})
            self.playback_pending = False
            self.active_playback_mark = None
            self.interruption_clears += 1
            emit("interruption.clear_sent", self.call_id, turn=self.turn_count)
            audit("twilio.media.clear", "call", self.call_id, {"reason": "caller_speech_start"})

    async def _send_twilio(self, payload: dict[str, Any]) -> None:
        async with self.send_lock:
            await self.websocket.send_json(payload)

    async def _cancel_reply(self) -> None:
        if self.reply_task and not self.reply_task.done():
            self.reply_task.cancel()
            await asyncio.gather(self.reply_task, return_exceptions=True)
        self.reply_task = None

    async def _queue_audio(self, pcm16: bytes) -> None:
        try:
            self.audio_queue.put_nowait(pcm16)
        except asyncio.QueueFull:
            audit("realtime.audio_dropped", "call", self.call_id, {"reason": "stt_queue_full"})

    def _store_turn(self, speaker: str, text: str) -> None:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_turns
                    (id, call_id, speaker, text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (new_id("turn"), self.call_id, speaker, text, now_iso()),
            )

    def _update_outcome(self, outcome: str) -> None:
        opt_out = int(outcome == "opted_out")
        with connect() as conn:
            conn.execute(
                "UPDATE calls SET outcome = ?, opt_out_detected = ?, status = 'completed' WHERE id = ?",
                (outcome, opt_out, self.call_id),
            )
            if outcome == "opted_out":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO suppression_entries
                        (id, client_id, phone_e164, reason, source_call_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("suppression"),
                        self.state.campaign["client_id"],
                        self.state.lead["phone_e164"],
                        "voice_opt_out",
                        self.call_id,
                        now_iso(),
                    ),
                )
                conn.execute(
                    "UPDATE leads SET status = 'suppressed', suppressed_at = ? WHERE id = ?",
                    (now_iso(), self.state.lead["id"]),
                )
        audit("call.outcome_detected", "call", self.call_id, {"outcome": outcome})

    def _persist_media_count(self) -> None:
        with connect() as conn:
            row = conn.execute("SELECT metadata_json FROM calls WHERE id = ?", (self.call_id,)).fetchone()
            if row:
                metadata = {}
                try:
                    import json

                    metadata = json.loads(row["metadata_json"] or "{}")
                except json.JSONDecodeError:
                    metadata = {}
                metadata["media_events"] = self.media_events
                conn.execute("UPDATE calls SET metadata_json = ? WHERE id = ?", (json_dump(metadata), self.call_id))

