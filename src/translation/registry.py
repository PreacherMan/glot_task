from typing import Optional

from .conversation import Conversation, SessionFactory


class ConversationRegistry:
    """
    In-memory tracking of currently-live Conversations, keyed by
    conversation_id. Needed regardless of whether persistence is ever
    built — without this, nothing can route an incoming message to
    the right Conversation, or answer "what's currently active" at
    all. Deliberately not persistence: this state is only ever "what's
    live in this running process right now" — nothing survives a
    restart, and nothing here needs a database to be genuinely useful.
    """

    def __init__(self):
        self._conversations: dict[str, Conversation] = {}

    def create(
        self, conversation_id: str, lang_a: str, lang_b: str, session_factory: SessionFactory
    ) -> Conversation:
        conversation = Conversation(lang_a, lang_b, session_factory)
        self._conversations[conversation_id] = conversation
        return conversation

    def get(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)

    async def end(self, conversation_id: str) -> None:
        conversation = self._conversations.pop(conversation_id, None)
        if conversation:
            await conversation.close()
