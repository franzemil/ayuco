from __future__ import annotations

from ayuco.domain.entities.message import ToolResult
from ayuco.domain.ports.tool_provider import ToolProvider


class ExecuteTool:
    def __init__(self, providers: list[ToolProvider]) -> None:
        self._providers = providers

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        for provider in self._providers:
            tools = await provider.list_tools()
            if any(t["name"] == name for t in tools):
                return await provider.execute(name, arguments)
        return ToolResult(
            call_id="",
            content=f"Unknown tool: {name}",
            is_error=True,
        )
