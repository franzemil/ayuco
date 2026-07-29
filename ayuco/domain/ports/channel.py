from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from ayuco.domain.entities.message import Message

MessageHandler = Callable[[str, str], Awaitable[Message]]


@runtime_checkable
class Channel(Protocol):
    async def send(self, chat_id: str, message: Message) -> None: ...

    async def start(self, handler: MessageHandler) -> None: ...

    async def run(self) -> None: ...
