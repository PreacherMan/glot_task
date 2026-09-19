import asyncio
import json
import os

import websockets

from ..session import EventType, TranslationEvent, TranslationSession

REALTIME_TRANSLATIONS_URL = "wss://api.openai.com/v1/realtime/translations?model=gpt-realtime-translate"


class OpenAIRealtimeSession(TranslationSession):
    """
    Real implementation against OpenAI's Realtime Translation WebSocket
    API. Deliberately built async-native (via `websockets`, not the
    docs' own synchronous `websocket-client` example) — the docs'
    example illustrates the protocol for a single connection, not an
    architecture for a platform running many concurrent sessions.

    Untestable without real API credentials — see providers/fake.py
    for the implementation this skeleton actually runs and tests
    against.
    """

    def __init__(self, source_lang: str, target_lang: str):
        super().__init__(source_lang, target_lang)
        self._ws = None
        self._queue: "asyncio.Queue[TranslationEvent]" = asyncio.Queue()
        self._closed = False

    async def start(self) -> None:
        self._ws = await websockets.connect(
            REALTIME_TRANSLATIONS_URL,
            additional_headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "OpenAI-Safety-Identifier": "hashed-user-id",
            },
        )
        await self._ws.send(json.dumps({
            "type": "session.update",
            "session": {"audio": {"output": {"language": self.target_lang}}},
        }))
        asyncio.create_task(self._receive_loop())

    async def send_audio(self, chunk: bytes) -> None:
        await self._ws.send(json.dumps({
            "type": "session.input_audio_buffer.append",
            "audio": chunk.decode("ascii"),  # caller is responsible for base64-encoding PCM16 first
        }))

    async def _receive_loop(self) -> None:
        try:
            async for raw in self._ws:
                event = json.loads(raw)
                if event["type"] == "session.output_audio.delta":
                    await self._queue.put(TranslationEvent(EventType.AUDIO_DELTA, event["delta"]))
                elif event["type"] == "session.output_transcript.delta":
                    await self._queue.put(TranslationEvent(EventType.TRANSCRIPT_DELTA, event["delta"]))
                elif event["type"] == "session.closed":
                    self._closed = True
        finally:
            # The connection can also close at the transport level
            # (e.g. the server ending the session normally via voice-
            # activity detection) without a clean session.closed
            # message ever arriving — the async for above simply ends
            # on its own in that case. Either way, once this loop is
            # genuinely done, events() needs to know, or it polls an
            # empty queue forever waiting for a signal that's never
            # coming.
            self._closed = True

    async def events(self):
        while not self._closed or not self._queue.empty():
            try:
                yield await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        # Per the docs: send session.close and keep reading until
        # session.closed arrives, so translated output still draining
        # from the session isn't dropped.
        await self._ws.send(json.dumps({"type": "session.close"}))
