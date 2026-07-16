from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class CLIBot:
    """Simple stdin/stdout adapter for testing without Telegram."""

    def __init__(self) -> None:
        self._handler = None

    async def start(self, handler) -> None:
        self._handler = handler

    async def run(self) -> None:
        logger.info("Ayuco CLI mode. Type your message (Ctrl+C to quit).")
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
