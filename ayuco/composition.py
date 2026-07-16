from __future__ import annotations

import logging

from ayuco.adapters.cli import CLIBot
from ayuco.adapters.telegram.bot import TelegramChannel
from ayuco.domain.use_cases.handle_message import HandleMessage
from ayuco.infrastructure.llm.openai_provider import OpenAIProvider
from ayuco.infrastructure.mcp.mcp_tool_provider import MCPToolProvider
from ayuco.infrastructure.memory.sliding_window import SlidingWindowMemory
from ayuco.infrastructure.memory.summarizer import SummarizedMemory
from ayuco.infrastructure.persistence.message_repository import SQLiteMessageRepository
from ayuco.infrastructure.sandbox.bwrap_executor import BwrapExecutor
from ayuco.infrastructure.sandbox.tool_provider import SandboxToolProvider

logger = logging.getLogger(__name__)


async def build(config: dict, cli_mode: bool = False):  # type: ignore[no-untyped-def]
    # --- persistence ---
    repo = SQLiteMessageRepository(config["storage"]["db_path"])
    await repo.connect()

    # --- llm ---
    llm = OpenAIProvider(
        base_url=config["llm"]["base_url"],
        api_key=config["llm"]["api_key"],
        model=config["llm"]["model"],
    )

    # --- memory ---
    mem_cfg = config["memory"]
    if mem_cfg["mode"] == "summarized":
        memory = SummarizedMemory(
            repo,
            llm,
            max_messages=mem_cfg["max_messages"],
            summarize_threshold=mem_cfg["summarize_threshold"],
        )
    else:
        memory = SlidingWindowMemory(repo, max_messages=mem_cfg["max_messages"])

    # --- tools ---
    providers = []
    if config["sandbox"]["enabled"]:
        executor = BwrapExecutor(
            bwrap_path=config["sandbox"]["bwrap_path"],
            timeout=config["sandbox"]["timeout"],
            allowed_commands=config["sandbox"]["allowed_commands"],
        )
        providers.append(SandboxToolProvider(executor))

    for server_cfg in config["mcp"]["servers"]:
        mcp = MCPToolProvider(server_cfg)
        await mcp.connect()
        providers.append(mcp)

    # --- use case ---
    handle_message = HandleMessage(
        repo=repo,
        llm=llm,
        memory=memory,
        providers=providers,
        system_prompt=config["llm"].get("system_prompt", ""),
    )

    # --- adapter ---
    if cli_mode:
        channel = CLIBot()
    else:
        channel = TelegramChannel(config["telegram"]["token"])
        channel.on_clear(repo.clear)

    await channel.start(handle_message)

    return channel
