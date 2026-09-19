import asyncio

from src.translation.broadcast import Broadcast
from src.translation.providers.fake import FakeTranslationSession


async def _run():
    # Proves the fan-out genuinely reaches every target language, not
    # just the first one — one send_audio() call should produce a
    # correctly-translated event on each of the two sessions below.
    broadcast = Broadcast("en", ["es", "fr"], session_factory=FakeTranslationSession)
    await broadcast.start()

    await broadcast.send_audio(b"hello")

    es_event = await broadcast.sessions["es"].events().__anext__()
    fr_event = await broadcast.sessions["fr"].events().__anext__()

    assert es_event.data == "[es] hello", es_event.data
    assert fr_event.data == "[fr] hello", fr_event.data

    await broadcast.close()
    print("ok: broadcast fans one speaker's audio out to every target language correctly")


def test_broadcast_fans_out_to_all_targets():
    asyncio.run(_run())


if __name__ == "__main__":
    test_broadcast_fans_out_to_all_targets()
