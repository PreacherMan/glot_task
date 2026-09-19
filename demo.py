"""
Runnable demo — not a test, a human-readable walkthrough of a real
conversation composed from two independent TranslationSessions.

    python3 -m demo
"""
import asyncio

from src.translation.conversation import Conversation
from src.translation.providers.fake import FakeTranslationSession


async def main():
    print("Starting a conversation: participant A speaks English, participant B speaks Spanish.\n")
    conversation = Conversation("en", "es", session_factory=FakeTranslationSession)
    await conversation.start()

    turns = [
        ("a", "Hello, how are you?"),
        ("b", "Muy bien, gracias!"),
        ("a", "Glad to hear it."),
    ]

    for speaker, text in turns:
        if speaker == "a":
            print(f"A (en) says: {text}")
            await conversation.send_from_a(text.encode("utf-8"))
            event = await conversation.a_to_b.events().__anext__()
            print(f"  -> B hears: {event.data}\n")
        else:
            print(f"B (es) says: {text}")
            await conversation.send_from_b(text.encode("utf-8"))
            event = await conversation.b_to_a.events().__anext__()
            print(f"  -> A hears: {event.data}\n")

    await conversation.close()
    print("Conversation closed cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
