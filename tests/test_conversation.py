import asyncio

from src.translation.conversation import Conversation
from src.translation.providers.fake import FakeTranslationSession


async def _run():
    # The one line that matters: Conversation only ever receives a
    # factory — it never imports FakeTranslationSession itself, and
    # would work identically with a factory producing real
    # OpenAIRealtimeSession instances instead. This is the actual
    # proof that provider-agnosticism holds in running code, not just
    # in the design doc's prose.
    conversation = Conversation("en", "es", session_factory=FakeTranslationSession)
    await conversation.start()

    await conversation.send_from_a(b"hello")
    event = await conversation.a_to_b.events().__anext__()
    assert event.data == "[es] hello", event.data

    await conversation.send_from_b(b"hola")
    event = await conversation.b_to_a.events().__anext__()
    assert event.data == "[en] hola", event.data

    await conversation.close()
    print("ok: conversation composes two independent sessions correctly")


def test_conversation_translates_both_directions():
    asyncio.run(_run())


if __name__ == "__main__":
    test_conversation_translates_both_directions()
