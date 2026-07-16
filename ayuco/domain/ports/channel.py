from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

MessageHandler = Callable[[str, str], Awaitable[str]]


@runtime_checkable
class Channel(Protocol):
    async def send(self, chat_id: str, content: str) -> None: ...

    async def start(self, handler: MessageHandler) -> None: ...

    async def run(self) -> None: ...
