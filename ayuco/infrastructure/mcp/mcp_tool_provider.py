from __future__ import annotations

from typing import Any

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ayuco.domain.entities.message import ToolResult

log = structlog.get_logger()


class MCPToolProvider:
    def __init__(self, server_config: dict[str, Any]) -> None:
        self._name = server_config["name"]
        self._command = server_config["command"]
        self._transport = server_config.get("transport", "stdio")
        self._session: ClientSession | None = None
        self._tools: list[dict] | None = None
        self._cm: Any = None
        self._session_cm: Any = None

    async def connect(self) -> None:
        if self._transport != "stdio":
            log.warning(
                "mcp_unsupported_transport",
                server=self._name,
                transport=self._transport,
            )
            return
        try:
            params = StdioServerParameters(
                command=self._command[0],
                args=self._command[1:] if len(self._command) > 1 else [],
            )
            self._cm = stdio_client(params)
            read, write = await self._cm.__aenter__()
            self._session_cm = ClientSession(read, write)
            self._session = await self._session_cm.__aenter__()
            await self._session.initialize()
            log.info("mcp_connected", server=self._name)
        except Exception:
            log.exception("mcp_connect_failed", server=self._name)
            self._session = None

    async def close(self) -> None:
        if self._session_cm:
            await self._session_cm.__aexit__(None, None, None)
        if self._cm:
            await self._cm.__aexit__(None, None, None)

    async def list_tools(self) -> list[dict]:
        if self._session is None:
            return []
        if self._tools is not None:
            return self._tools
        try:
            result = await self._session.list_tools()
            self._tools = [
                {
                    "name": f"mcp_{self._name}_{tool.name}",
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                }
                for tool in result.tools
            ]
            return self._tools
        except Exception:
            log.exception("mcp_list_tools_failed", server=self._name)
            return []

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        if self._session is None:
            return ToolResult(call_id="", content="MCP server not connected", is_error=True)
        prefix = f"mcp_{self._name}_"
        real_name = name.removeprefix(prefix) if name.startswith(prefix) else name
        try:
            result = await self._session.call_tool(real_name, arguments)
            content = ""
            for item in result.content:
                if hasattr(item, "text"):
                    content += item.text
                else:
                    content += str(item)
            return ToolResult(call_id="", content=content or "(no output)")
        except Exception as e:
            return ToolResult(call_id="", content=str(e), is_error=True)
