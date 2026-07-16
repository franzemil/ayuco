from __future__ import annotations

import logging

from ayuco.domain.entities.message import Message, Role
from ayuco.domain.ports.llm import LLMProvider
from ayuco.domain.ports.repository import MessageRepository

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = (
    "Summarize the following conversation into a concise paragraph. "
    "Focus on key facts, decisions, and context. "
    "Be brief but preserve important details."
)


class SummarizedMemory:
    def __init__(
        self,
        repo: MessageRepository,
        llm: LLMProvider,
        max_messages: int = 40,
        summarize_threshold: int = 100,
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._max_messages = max_messages
        self._summarize_threshold = summarize_threshold

    async def load_context(self, chat_id: str) -> list[Message]:
        history = await self._repo.get_history(chat_id, self._summarize_threshold)

        if len(history) >= self._summarize_threshold:
            await self._maybe_summarize(chat_id, history)

        summary = await self._repo.get_summarized(chat_id)
        recent = await self._repo.get_history(chat_id, self._max_messages)

        context: list[Message] = []
        if summary:
            context.append(
                Message(
                    chat_id=chat_id,
                    role=Role.SYSTEM,
                    content=f"Summary of earlier conversation:\n{summary}",
                )
            )
        context.extend(recent)
        return context

    async def _maybe_summarize(self, chat_id: str, history: list[Message]) -> None:
        existing = await self._repo.get_summarized(chat_id)
        conv_text = "\n".join(f"{m.role.value}: {m.content}" for m in history if m.content)
        if not conv_text.strip():
            return

        msgs = [
            Message(chat_id=chat_id, role=Role.SYSTEM, content=SUMMARY_SYSTEM),
            Message(chat_id=chat_id, role=Role.USER, content=conv_text),
        ]
        try:
            resp = await self._llm.chat(msgs)
            if resp.content:
                combined = f"{existing}\n\n{resp.content}" if existing else resp.content
                await self._repo.set_summary(chat_id, combined)
                logger.info("Summarized conversation for chat %s", chat_id)
        except Exception:
            logger.exception("Failed to summarize chat %s", chat_id)
