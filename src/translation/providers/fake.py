import asyncio

from ..session import EventType, TranslationEvent, TranslationSession


class FakeTranslationSession(TranslationSession):
    """
    In-memory fake — no network, no real audio decoding. Treats incoming
    "audio" bytes as UTF-8 text and echoes it back prefixed with the
    target language, so tests can assert on exact, predictable output.
    Exists to prove the orchestration layer above genuinely works
    end-to-end without needing real provider credentials.
    """

    def __init__(self, source_lang: str, target_lang: str):
        super().__init__(source_lang, target_lang)
        self._queue: "asyncio.Queue[TranslationEvent]" = asyncio.Queue()
        self._closed = False

    async def start(self) -> None:
        pass

    async def send_audio(self, chunk: bytes) -> None:
        text = chunk.decode("utf-8")
        translated = f"[{self.target_lang}] {text}"
        await self._queue.put(TranslationEvent(EventType.TRANSCRIPT_DELTA, translated))

    async def events(self):
        # Drains any remaining queued events after close() before
        # stopping — mirrors the real API's session.close -> flush
        # pending output -> session.closed handshake.
        while not self._closed or not self._queue.empty():
            try:
                yield await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        self._closed = True
