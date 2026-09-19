# Cross-Language Conversation Platform

A small, runnable skeleton for a cross-language conversation platform,
built on top of a Realtime Translation WebSocket API. See
`design/DESIGN.md` for architecture, key decisions, and trade-offs.

## Setup

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the demo (free, no credentials needed)

Runs entirely on an in-memory fake provider — proves the
`Conversation`/`ConversationRegistry` orchestration works correctly,
with zero external dependencies or cost.

```
python3 -m demo
```

## Run against the real API (costs real money)

Requires a real OpenAI API key, set in `.env`:

```
OPENAI_API_KEY=your-key-here
```

Then, with a short PCM16 audio file (24kHz, mono) to hand:

```
python3 try_real_api.py hello.pcm
```

Prints the live translated transcript as it streams in, and saves
the translated audio to `translated.pcm` (convert to something
playable with `ffmpeg -f s16le -ar 24000 -ac 1 -i translated.pcm
translated.wav`).

## Run the tests

```
pytest tests/ -v --junitxml=test-report.xml
```

Writes a real, structured test report to `test-report.xml`, in the
same format standard CI systems consume directly.
