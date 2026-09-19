from typing import List

from .conversation import SessionFactory


class Broadcast:
    """
    One speaker, many listeners in different target languages —
    matching the real API's own documented "listen-along" pattern
    (one session per target language, from a single source). Like
    Conversation, depends only on the abstract TranslationSession
    interface via a factory — proves provider-agnosticism holds under
    a second, differently-shaped use case, not just the two-person
    conversation.
    """

    def __init__(self, source_lang: str, target_langs: List[str], session_factory: SessionFactory):
        self.sessions = {
            target_lang: session_factory(source_lang, target_lang)
            for target_lang in target_langs
        }

    async def start(self) -> None:
        for session in self.sessions.values():
            await session.start()

    async def send_audio(self, chunk: bytes) -> None:
        for session in self.sessions.values():
            await session.send_audio(chunk)

    async def close(self) -> None:
        for session in self.sessions.values():
            await session.close()
