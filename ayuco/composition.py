from __future__ import annotations

import structlog

from ayuco.adapters.cli import CLIBot
from ayuco.adapters.telegram.bot import TelegramChannel
from ayuco.config import Settings
from ayuco.domain.use_cases.handle_message import HandleMessage
from ayuco.infrastructure.llm.openai_provider import OpenAIProvider
from ayuco.infrastructure.mcp.mcp_tool_provider import MCPToolProvider
from ayuco.infrastructure.memory.sliding_window import SlidingWindowMemory
from ayuco.infrastructure.memory.summarizer import SummarizedMemory
from ayuco.infrastructure.persistence.message_repository import SQLiteMessageRepository
from ayuco.infrastructure.sandbox.bwrap_executor import BwrapExecutor
from ayuco.infrastructure.sandbox.tool_provider import SandboxToolProvider

log = structlog.get_logger()


async def build(settings: Settings, cli_mode: bool = False):  # type: ignore[no-untyped-def]
    # --- persistence ---
    repo = SQLiteMessageRepository(settings.storage.db_path)
    await repo.connect()

    # --- llm ---
    llm = OpenAIProvider(
        base_url=settings.llm.base_url,
        api_key=settings.llm.api_key,
        model=settings.llm.model,
    )

    # --- memory ---
    if settings.memory.mode == "summarized":
        memory = SummarizedMemory(
            repo,
            llm,
            max_messages=settings.memory.max_messages,
            summarize_threshold=settings.memory.summarize_threshold,
        )
    else:
        memory = SlidingWindowMemory(repo, max_messages=settings.memory.max_messages)

    # --- tools ---
    providers = []
    if settings.sandbox.enabled:
        executor = BwrapExecutor(
            bwrap_path=settings.sandbox.bwrap_path,
            timeout=settings.sandbox.timeout,
            allowed_commands=settings.sandbox.allowed_commands,
        )
        providers.append(SandboxToolProvider(executor))

    for server_cfg in settings.mcp.servers:
        mcp = MCPToolProvider(server_cfg.model_dump())
        await mcp.connect()
        providers.append(mcp)

    # --- use case ---
    handle_message = HandleMessage(
        repo=repo,
        llm=llm,
        memory=memory,
        providers=providers,
        system_prompt=settings.llm.system_prompt,
    )

    # --- adapter ---
    if cli_mode:
        channel = CLIBot()
    else:
        channel = TelegramChannel(settings.telegram.token)
        channel.on_clear(repo.clear)

    await channel.start(handle_message)
    log.info(
        "app_built",
        sandbox=settings.sandbox.enabled,
        mcp_servers=len(settings.mcp.servers),
        memory_mode=settings.memory.mode,
    )
    return channel
