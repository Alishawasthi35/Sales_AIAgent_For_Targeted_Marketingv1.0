import asyncio
from types import SimpleNamespace

from app.realtime import RealtimeCallBridge


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, value):
        self.sent.append(value)


def bridge():
    socket = FakeWebSocket()
    instance = RealtimeCallBridge(socket, "call_test", {}, {})
    instance.stream_sid = "stream_test"
    return instance, socket


def test_tts_sends_first_chunk_before_synthesis_finishes(monkeypatch):
    async def scenario():
        instance, socket = bridge()
        release = asyncio.Event()

        async def chunks(_text):
            yield "first"
            await release.wait()
            yield "second"

        monkeypatch.setattr("app.realtime.stream_twilio_mulaw_chunks", chunks)
        task = asyncio.create_task(instance._speak("hello", "opening"))
        for _ in range(20):
            if socket.sent:
                break
            await asyncio.sleep(0)
        assert socket.sent[0]["media"]["payload"] == "first"
        assert not task.done()
        release.set()
        await task
        assert [item["event"] for item in socket.sent] == ["media", "media", "mark"]

    asyncio.run(scenario())


def test_speech_start_cancels_reply_and_clears_playback():
    async def scenario():
        instance, socket = bridge()
        instance.playback_pending = True
        instance.reply_task = asyncio.create_task(asyncio.sleep(60))

        class FakeSTT:
            async def recv(self):
                if not hasattr(self, "sent"):
                    self.sent = True
                    return SimpleNamespace(type="events", data=SimpleNamespace(signal_type="START_SPEECH"))
                await asyncio.sleep(60)

        receiver = asyncio.create_task(instance._receive_stt_messages(FakeSTT()))
        for _ in range(20):
            if socket.sent:
                break
            await asyncio.sleep(0)
        receiver.cancel()
        await asyncio.gather(receiver, return_exceptions=True)
        assert socket.sent == [{"event": "clear", "streamSid": "stream_test"}]
        assert instance.interruption_attempts == 1
        assert instance.interruption_clears == 1
        assert instance.reply_task is None

    asyncio.run(scenario())


def test_stale_mark_after_clear_does_not_end_new_playback(monkeypatch):
    monkeypatch.setattr("app.realtime.audit", lambda *args, **kwargs: None)
    async def scenario():
        instance, _ = bridge()
        instance.playback_pending = True
        instance.active_playback_mark = "turn-1"
        await instance._clear_playback()
        instance.playback_pending = True
        instance.active_playback_mark = "turn-2"

        class FakeSocket:
            async def receive_json(self):
                if not hasattr(self, "sent"):
                    self.sent = True
                    return {"event": "mark", "mark": {"name": "turn-1"}}
                return {"event": "stop"}

        instance.websocket = FakeSocket()
        await instance._receive_twilio_loop()
        assert instance.playback_pending
        assert instance.active_playback_mark == "turn-2"

    asyncio.run(scenario())
