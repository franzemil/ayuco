from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

from ayuco.domain.entities.message import Message, Role, ToolResult
from ayuco.domain.ports.channel import Channel
from ayuco.domain.ports.llm import LLMProvider
from ayuco.domain.ports.memory import MemoryManager
from ayuco.domain.ports.repository import MessageRepository
from ayuco.domain.ports.tool_provider import ToolProvider
from ayuco.domain.use_cases.execute_tool import ExecuteTool

log = structlog.get_logger()

MAX_TOOL_ROUNDS = 5


@dataclass
class _LoopResult:
    content: str
    usage: dict = field(default_factory=dict)
    total_llm_time: float = 0.0


class HandleMessage:
    def __init__(
        self,
        repo: MessageRepository,
        llm: LLMProvider,
        memory: MemoryManager,
        providers: list[ToolProvider],
        system_prompt: str = "",
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._memory = memory
        self._execute_tool = ExecuteTool(providers)
        self._system_prompt = system_prompt
        self._channel: Channel | None = None
        self._tool_schemas: list[dict] | None = None
        self._providers = providers

    def set_channel(self, channel: Channel) -> None:
        self._channel = channel

    async def _gather_tools(self) -> list[dict]:
        if self._tool_schemas is not None:
            return self._tool_schemas
        schemas: list[dict] = []
        for provider in self._providers:
            schemas.extend(await provider.list_tools())
        self._tool_schemas = schemas
        return schemas

    async def __call__(self, chat_id: str, content: str) -> Message:
        inbound = Message(chat_id=chat_id, role=Role.USER, content=content)
        await self._repo.add(inbound)

        context = await self._memory.load_context(chat_id)
        tools = await self._gather_tools()

        if self._system_prompt:
            system = Message(
                chat_id=chat_id,
                role=Role.SYSTEM,
                content=self._system_prompt,
            )
            context = [system, *context]

        result = await self._loop(context, tools)

        outbound = Message(
            chat_id=chat_id,
            role=Role.ASSISTANT,
            content=result.content,
            generation_time=result.total_llm_time,
            usage=result.usage,
        )
        await self._repo.add(outbound)
        return outbound

    async def _loop(
        self,
        context: list[Message],
        tools: list[dict],
        rounds: int = 0,
    ) -> _LoopResult:
        if rounds >= MAX_TOOL_ROUNDS:
            return _LoopResult(content="Too many tool calls in a row. Stopping.")

        t0 = time.perf_counter()
        llm_response = await self._llm.chat(context, tools or None)
        elapsed = time.perf_counter() - t0

        if not llm_response.tool_calls:
            return _LoopResult(
                content=llm_response.content,
                usage=llm_response.usage,
                total_llm_time=elapsed,
            )

        tool_messages = list(context)
        for tc in llm_response.tool_calls:
            log.info("tool_call", name=tc.name, arguments=tc.arguments)
            result = await self._execute_tool.execute(tc.name, tc.arguments)
            result = ToolResult(
                call_id=tc.id,
                content=result.content,
                is_error=result.is_error,
            )
            tool_messages.append(
                Message(
                    chat_id=context[0].chat_id if context else "",
                    role=Role.ASSISTANT,
                    content=None,
                    tool_calls=(tc,),
                    reasoning_content=llm_response.reasoning_content,
                )
            )
            tool_messages.append(
                Message(
                    chat_id=context[0].chat_id if context else "",
                    role=Role.TOOL,
                    content=result.content,
                    tool_result=result,
                )
            )
            if result.is_error:
                log.warning(
                    "tool_execution_failed",
                    name=tc.name,
                    error=result.content,
                )
                return _LoopResult(content=result.content)

        nested = await self._loop(tool_messages, tools, rounds + 1)
        nested.total_llm_time += elapsed
        return nested
