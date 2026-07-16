from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ayuco.domain.entities.message import Message, ToolCall


@dataclass(frozen=True)
class LLMResponse:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: dict = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse: ...
