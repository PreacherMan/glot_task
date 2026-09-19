import asyncio

from src.translation.registry import ConversationRegistry
from src.translation.providers.fake import FakeTranslationSession


async def _run():
    registry = ConversationRegistry()

    conversation = registry.create("conv_1", "en", "es", session_factory=FakeTranslationSession)
    await conversation.start()

    assert registry.get("conv_1") is conversation
    assert registry.get("does_not_exist") is None

    await registry.end("conv_1")
    assert registry.get("conv_1") is None
    # Proves end() genuinely propagates a real close down through
    # Conversation into both underlying sessions, not just that the
    # dict entry was removed — without this, the test would still
    # pass even if end() silently forgot to call close() at all.
    assert conversation.a_to_b._closed is True
    assert conversation.b_to_a._closed is True

    print("ok: registry creates, retrieves, and ends conversations correctly")


def test_registry_lifecycle():
    asyncio.run(_run())


if __name__ == "__main__":
    test_registry_lifecycle()
