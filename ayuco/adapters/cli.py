from __future__ import annotations

import asyncio

import structlog

from ayuco.domain.entities.message import Message

log = structlog.get_logger()


def _format_metadata(message: Message) -> str:
    parts = []
    if message.generation_time is not None:
        parts.append(f"\u26a1{message.generation_time:.1f}s")
    if message.usage:
        total = message.usage.get("total_tokens", 0)
        parts.append(f"\ud83d\udd24{total}tok")
    return f"  [{' | '.join(parts)}]" if parts else ""


class CLIBot:
    """Simple stdin/stdout adapter for testing without Telegram."""

    def __init__(self) -> None:
        self._handler = None

    async def start(self, handler) -> None:  # type: ignore[no-untyped-def]
        self._handler = handler

    async def run(self) -> None:
        log.info("cli_mode")
        loop = asyncio.get_event_loop()
        while True:
            try:
                text = await loop.run_in_executor(None, lambda: input("You: "))
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if not text.strip():
                continue
            response = await self._handler("cli", text)
            await self.send("cli", response)

    async def send(self, chat_id: str, message: Message) -> None:
        text = message.content + _format_metadata(message)
        print(f"Ayuco: {text}")
