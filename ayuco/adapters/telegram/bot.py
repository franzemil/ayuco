from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import structlog
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

log = structlog.get_logger()

MessageHandlerFunc = Callable[[str, str], Awaitable[str]]


class TelegramChannel:
    def __init__(self, token: str) -> None:
        self._token = token
        self._handler: MessageHandlerFunc | None = None
        self._clear_handler: Callable[[str], Awaitable[None]] | None = None
        self._app = ApplicationBuilder().token(token).build()

    def on_clear(self, handler: Callable[[str], Awaitable[None]]) -> None:
        self._clear_handler = handler

    async def start(self, handler: MessageHandlerFunc) -> None:
        self._handler = handler
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("clear", self._cmd_clear))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

    async def run(self) -> None:
        log.info("telegram_starting")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)
        log.info("telegram_running")
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except (KeyboardInterrupt, SystemExit):
            log.info("telegram_shutting_down")
            await self._app.stop()

    async def send(self, chat_id: str, content: str) -> None:
        for i in range(0, len(content), 4096):
            await self._app.bot.send_message(chat_id=int(chat_id), text=content[i : i + 4096])

    async def _on_text(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not self._handler:
            return
        chat_id = str(update.effective_chat.id)
        text = update.message.text or ""
        try:
            response = await self._handler(chat_id, text)
            await self.send(chat_id, response)
        except Exception:
            log.exception("telegram_message_error", chat_id=chat_id)
            await self.send(chat_id, "An error occurred while processing your message.")

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text("Hello! I'm Ayuco. Send me a message and I'll respond.")

    async def _cmd_clear(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            chat_id = str(update.effective_chat.id)
            if self._clear_handler:
                await self._clear_handler(chat_id)
            await update.message.reply_text("Context cleared. Starting fresh.")

    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(
                "Ayuco - Minimal AI Agent\n\n"
                "Just send me a message and I'll respond.\n\n"
                "Commands:\n"
                "/start - Welcome message\n"
                "/clear - Clear conversation context\n"
                "/help - Show this help"
            )
