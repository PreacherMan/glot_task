from typing import Callable

from .session import TranslationSession

# A factory, not a concrete provider — Conversation never imports
# FakeTranslationSession or OpenAIRealtimeSession directly. Whatever
# factory the caller passes in decides which provider actually runs
# underneath; this file has no way to know or care.
SessionFactory = Callable[[str, str], TranslationSession]


class Conversation:
    """
    A two-person, cross-language conversation — composed entirely from
    two independent, one-directional TranslationSessions, matching the
    real API's own documented pattern (one session per direction; see
    OpenAI's own docs: "Caller A audio -> translate into Caller B
    language -> play to Caller B", and the reverse).

    Depends only on the abstract TranslationSession interface via
    session_factory — this is what makes provider-agnosticism real
    rather than aspirational: swap the factory, nothing else in this
    class changes.
    """

    def __init__(self, lang_a: str, lang_b: str, session_factory: SessionFactory):
        self.a_to_b = session_factory(lang_a, lang_b)
        self.b_to_a = session_factory(lang_b, lang_a)

    async def start(self) -> None:
        await self.a_to_b.start()
        await self.b_to_a.start()

    async def send_from_a(self, chunk: bytes) -> None:
        await self.a_to_b.send_audio(chunk)

    async def send_from_b(self, chunk: bytes) -> None:
        await self.b_to_a.send_audio(chunk)

    async def close(self) -> None:
        await self.a_to_b.close()
        await self.b_to_a.close()
