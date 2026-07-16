from __future__ import annotations

from ayuco.domain.entities.message import Message
from ayuco.domain.ports.repository import MessageRepository


class SlidingWindowMemory:
    def __init__(self, repo: MessageRepository, max_messages: int = 40) -> None:
        self._repo = repo
        self._max_messages = max_messages

    async def load_context(self, chat_id: str) -> list[Message]:
        return await self._repo.get_history(chat_id, self._max_messages)
