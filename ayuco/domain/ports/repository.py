from __future__ import annotations

from typing import Protocol, runtime_checkable

from ayuco.domain.entities.message import Message


@runtime_checkable
class MessageRepository(Protocol):
    async def add(self, message: Message) -> None: ...

    async def get_history(self, chat_id: str, limit: int) -> list[Message]: ...

    async def get_summarized(self, chat_id: str) -> str | None: ...

    async def set_summary(self, chat_id: str, summary: str) -> None: ...

    async def clear(self, chat_id: str) -> None: ...
