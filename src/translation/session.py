from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Union


class EventType(Enum):
    AUDIO_DELTA = "audio_delta"
    TRANSCRIPT_DELTA = "transcript_delta"


@dataclass
class TranslationEvent:
    type: EventType
    data: Union[bytes, str]  # audio bytes for AUDIO_DELTA, text for TRANSCRIPT_DELTA


class TranslationSession(ABC):
    """
    One-way, one language-pair translation stream — the real primitive
    the underlying Realtime Translation API models (one session per
    source->target direction; see OpenAI's own docs: a two-person
    conversation needs two of these, one per direction; a group room
    needs active_speakers x target_languages of them).

    Higher-level use cases (broadcast, conversation, group rooms) are
    built entirely by composing multiple of these — this interface
    itself never knows what use case it's part of.
    """

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang

    @abstractmethod
    async def start(self) -> None:
        """Open the underlying connection/session."""

    @abstractmethod
    async def send_audio(self, chunk: bytes) -> None:
        """Feed a chunk of source audio into the session."""

    @abstractmethod
    def events(self) -> AsyncIterator[TranslationEvent]:
        """Yield translated audio/transcript deltas as they arrive."""

    @abstractmethod
    async def close(self) -> None:
        """Gracefully end the session, flushing any pending output."""
