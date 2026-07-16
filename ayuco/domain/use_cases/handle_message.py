from __future__ import annotations

import structlog

from ayuco.domain.entities.message import Message, Role
from ayuco.domain.ports.channel import Channel
from ayuco.domain.ports.llm import LLMProvider
from ayuco.domain.ports.memory import MemoryManager
from ayuco.domain.ports.repository import MessageRepository
from ayuco.domain.ports.tool_provider import ToolProvider
from ayuco.domain.use_cases.execute_tool import ExecuteTool

log = structlog.get_logger()

MAX_TOOL_ROUNDS = 5


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

    async def __call__(self, chat_id: str, content: str) -> str:
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

        response = await self._loop(context, tools)

        outbound = Message(
            chat_id=chat_id,
            role=Role.ASSISTANT,
            content=response,
        )
        await self._repo.add(outbound)
        return response

    async def _loop(
        self,
        context: list[Message],
        tools: list[dict],
        rounds: int = 0,
    ) -> str:
        if rounds >= MAX_TOOL_ROUNDS:
            return "Too many tool calls in a row. Stopping."

        llm_response = await self._llm.chat(context, tools or None)

        if not llm_response.tool_calls:
            return llm_response.content

        tool_messages = list(context)
        for tc in llm_response.tool_calls:
            log.info("tool_call", name=tc.name, arguments=tc.arguments)
            result = await self._execute_tool.execute(tc.name, tc.arguments)
            tool_messages.append(
                Message(
                    chat_id=context[0].chat_id if context else "",
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=(tc,),
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

        return await self._loop(tool_messages, tools, rounds + 1)
