from __future__ import annotations

import asyncio

import structlog

log = structlog.get_logger()


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
            print(f"Ayuco: {response}")

    async def send(self, chat_id: str, content: str) -> None:
        print(f"Ayuco: {content}")
