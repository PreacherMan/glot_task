# Cross-Language Conversation Platform — Design Doc

## Architecture

The platform is built around one deliberately small primitive: a
**TranslationSession** — one-way, one language pair. This mirrors the
real Realtime Translation API's own documented shape exactly (one
session per source→target direction; a two-person call needs two
sessions, one per direction; a group room needs
`active_speakers × target_languages` of them). The platform's actual
job is composing multiple of these correctly per use case — never
reinventing what a session is.

```
TranslationSession (abstract)
    ├── FakeTranslationSession   — in-memory, no network, drives every test/demo
    └── OpenAIRealtimeSession    — real WebSocket client against the provider

Conversation
    — composes 2 TranslationSessions (one per direction) via a factory
    — never imports a concrete provider directly

Broadcast
    — composes N TranslationSessions (one per target language) from a
      single source, via the same factory
    — proves the abstraction holds under a second, differently-shaped
      use case, not just the two-person conversation

ConversationRegistry
    — in-memory tracking of currently-live Conversations, keyed by id
    — genuinely needed regardless of persistence: without it, nothing
      can route an incoming message to the right Conversation

(described, not built — see "What I'd build next")
Outer API layer (FastAPI)
    POST /v1/conversations                 → returns conversation_id + websocket_url
    POST /v1/broadcasts                    → returns broadcast_id + websocket_url
    WS   /v1/conversations/{id}/stream      → participant_id-tagged audio in, for_participant_id-tagged audio/transcript out
    — internally just calls Conversation.send_from_a() / send_from_b(),
      routed by which participant_id sent the message
```

Bring-your-own-transport: the calling application owns microphone
access, device/participant UI, and how audio actually reaches us —
it streams into our WebSocket and plays back whatever comes out. This
platform never touches a device.

A C4 Context/Container diagram sits alongside this doc in `c4/` —
at this scale there's genuinely one container worth drawing: the
platform service itself, sitting between calling applications and
the underlying translation provider.

## Key decisions

**Session-per-direction, not a bidirectional abstraction.** This
isn't a design choice so much as a direct reflection of how the real
API actually works — modelling anything else would mean fighting the
provider's own shape rather than composing it.

**Async-native (`websockets`), not the docs' own synchronous
`websocket-client` example.** The docs' example illustrates the wire
protocol for a single connection, not an architecture for many
concurrent sessions sharing one process.

**Provider injected via factory function, never imported directly.**
`Conversation` depends only on the abstract `TranslationSession` type
and a `session_factory: Callable[[str, str], TranslationSession]`.
This is the actual, structural mechanism that makes
provider-agnosticism real rather than a claim in prose — swapping
`FakeTranslationSession` for a real `OpenAIRealtimeSession`, or later
a `GlotSession`, changes nothing else in `Conversation` at all.

**A second use case (`Broadcast`) reuses the same factory, proving
the abstraction genuinely generalises.** One speaker, many listeners
in different target languages — matching the real API's own
documented "listen-along" pattern. `Broadcast` composes N sessions
from a single source, keyed by target language in a dict rather than
the two named directions `Conversation` uses, since the two use cases
genuinely have different shapes. Sharing `session_factory`'s own type
across both, rather than each defining its own, is deliberate: two
real use cases now depend on the same provider boundary, not one.

**A fake provider drives every automated test; the real provider has
been genuinely exercised too.** `FakeTranslationSession` treats
incoming "audio" bytes as UTF-8 text and echoes them back prefixed
with the target language — deliberately fake translation, genuine
proof that the orchestration above it (session timing, routing,
direction) works correctly, with zero external dependencies or cost.
`demo.py` and all three test files run entirely on this. Separately,
`try_real_api.py` was run against the real API with a genuine short
audio recording, confirming the real `OpenAIRealtimeSession`
implementation actually works end-to-end, not just on paper.

`tests/` (`test_conversation.py`, `test_broadcast.py`,
`test_registry.py`) run via `pytest`, producing a real, structured
JUnit-XML report (`pytest tests/ -v --junitxml=test-report.xml`).

**Outer HTTP/WebSocket API layer: described, not built.** FastAPI is
the concrete choice, and the request/response shapes are sketched
above. It isn't implemented, because it's real but largely
boilerplate — the brief's own evaluation criteria (abstraction
quality, module boundaries, provider-agnosticism) live entirely in
the `translation/` package already built and tested, not in the
outer wiring.

## Trade-offs

The brief is explicit about preferring a tight, correctly-scoped
skeleton over broad, polished-looking coverage with no real point of
view behind it. That governed every choice here — two use cases, both
fully composed and tested, rather than a wider spread of half-built
ones. The second (`Broadcast`) earns its place specifically because it
proves the primitive generalises; a third would not have added an
argument the first two don't already make.

Deliberately not built, each for a specific reason rather than a lack
of time:
- **Auth / tenant isolation** — the skeleton is single-tenant by
  construction: there is no tenant concept anywhere in it, rather than
  a half-built one. Both arrive together (see "What I'd build next"),
  since a tenant-scoped registry is meaningless until the tenant id is
  trustworthy.
- **Persistence** — `ConversationRegistry` already handles session
  lifecycle (create, look up, end) entirely in memory; a real database
  only becomes necessary once state needs to survive a restart or be
  shared across multiple processes.
- **The outer API layer** — see above.
- **Group-room orchestration** — genuinely more complex (dynamic
  speaker join/leave, `N × M` session management) and deliberately
  left to the backlog rather than built quickly and shallowly.
- **Observability/metrics** — real and needed in production, not
  useful to fake in a demo with no real traffic.

## What I'd build next

1. **A second real provider connector (Glot's own API).** The single
   highest-value next step — it's the one thing that would prove the
   abstraction holds under a second real implementation, not just a
   fake one, and now against two genuinely different use cases
   (`Conversation` and `Broadcast`), not one. Expands by adding one
   new file (`providers/glot.py`) implementing the same
   `TranslationSession` interface; nothing else in the codebase
   changes.

2. **Auth + tenant isolation.** Real credentials, issued per
   customer, checked at the outer API layer — tenant identity derived
   from the credential, never from a field the caller supplies. These
   two land together or not at all: `ConversationRegistry.get()`
   currently returns any conversation to anyone holding the id, which
   is correct for a single-tenant skeleton and wrong the moment there
   are two customers. The lookup becomes tenant-scoped, so another
   tenant's conversation cannot be returned rather than being checked
   for after the fact. Process-level separation (shared pool by
   default, dedicated deployment where compliance demands it) is a
   deployment decision on top, not a code change.

3. **Group-room orchestration.** A `Room` class alongside
   `Conversation`, managing `N` speakers × `M` target languages,
   creating/tearing down sessions as speakers join and leave.
   Expands by composing the same `TranslationSession` primitive
   differently, in the same way `Conversation` already does for two
   participants.

4. **Durable persistence.** `ConversationRegistry` already tracks
   every currently-live conversation within a single running process
   — what's genuinely still missing is state surviving a restart or
   being shared across multiple processes/instances. Expands behind a
   small storage interface from the start, so which real database
   backs it (Postgres, say) stays swappable the same way the
   translation provider already is.

5. **Observability** — latency tracked separately from translation
   quality, session health, reconnect handling. Lifted directly from
   the real API docs' own production checklist. Expands by wrapping
   the existing `events()` stream with timing/logging, without
   touching the orchestration logic itself.
