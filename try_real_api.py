"""
Live test against the real OpenAI Realtime Translation API — costs
real money ($0.034/min of input audio), unlike demo.py which is free
and runs entirely on the fake provider. Requires OPENAI_API_KEY set
as an environment variable.

    export OPENAI_API_KEY=sk-...
    python3 try_real_api.py hello.pcm
"""
import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from src.translation.providers.openai_realtime import OpenAIRealtimeSession

CHUNK_SIZE = 4800  # bytes per chunk, matching the docs' own example


async def main(pcm_path: str):
    session = OpenAIRealtimeSession(source_lang="en", target_lang="es")

    print("Connecting to the real API...")
    await session.start()
    print("Connected. Streaming audio...")

    output_chunks = []

    async def consume_events():
        async for event in session.events():
            if event.type.value == "transcript_delta":
                print(f"  transcript: {event.data}", end="", flush=True)
            elif event.type.value == "audio_delta":
                output_chunks.append(event.data)

    consumer_task = asyncio.create_task(consume_events())

    with open(pcm_path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            try:
                await session.send_audio(chunk)
            except Exception as e:
                # The server can close the session normally (e.g. voice-
                # activity detection deciding the utterance is complete)
                # before we've finished sending every chunk in the file.
                # Stop sending, but let the consumer task drain whatever
                # translated output already arrived.
                print(f"\nSession ended while sending audio ({e}). Stopping send loop.")
                break
            await asyncio.sleep(0.05)  # rough pacing, not a real-time clock

    print("\nFinished sending audio. Closing session...")
    try:
        await session.close()
    except Exception:
        pass  # connection may already be closed by the server
    await asyncio.wait_for(consumer_task, timeout=10)

    if output_chunks:
        with open("translated.pcm", "wb") as out:
            out.write(b"".join(output_chunks))
        print("Translated audio saved to translated.pcm")
        print("Convert back to something playable with:")
        print("  ffmpeg -f s16le -ar 24000 -ac 1 -i translated.pcm translated.wav")
    else:
        print("No audio received back — check the transcript output above.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 try_real_api.py <path-to-pcm-file>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
