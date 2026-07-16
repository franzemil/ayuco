from __future__ import annotations

from typing import Protocol, runtime_checkable

from ayuco.domain.entities.message import Message


@runtime_checkable
class MemoryManager(Protocol):
    async def load_context(self, chat_id: str) -> list[Message]: ...
