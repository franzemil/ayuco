from __future__ import annotations

from ayuco.domain.entities.message import Message
from ayuco.domain.ports.memory import MemoryManager


class LoadContext:
    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    async def execute(self, chat_id: str) -> list[Message]:
        return await self._memory.load_context(chat_id)
