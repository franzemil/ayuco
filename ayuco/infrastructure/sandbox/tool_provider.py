from __future__ import annotations

from ayuco.domain.entities.message import ToolResult
from ayuco.infrastructure.sandbox.bwrap_executor import BwrapExecutor


class SandboxToolProvider:
    TOOL_NAME = "run_command"

    TOOL_SCHEMA = {
        "name": "run_command",
        "description": "Execute a shell command in a sandboxed environment",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
            },
            "required": ["command"],
        },
    }

    def __init__(self, executor: BwrapExecutor) -> None:
        self._executor = executor

    async def list_tools(self) -> list[dict]:
        return [self.TOOL_SCHEMA]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        return await self._executor.execute(name, arguments)
