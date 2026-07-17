from __future__ import annotations

from typing import ClassVar

from ayuco.domain.entities.message import ToolResult
from ayuco.infrastructure.sandbox.bwrap_executor import BwrapExecutor


class SandboxToolProvider:
    TOOL_NAME: ClassVar[str] = "run_command"

    TOOL_SCHEMA: ClassVar[dict] = {
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

    def __init__(self, executor: BwrapExecutor, *, sandboxed: bool = True) -> None:
        self._executor = executor
        self._sandboxed = sandboxed

    async def list_tools(self) -> list[dict]:
        schema = dict(self.TOOL_SCHEMA)
        if not self._sandboxed:
            schema = {
                **schema,
                "description": "Execute a shell command",
            }
        return [schema]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        return await self._executor.execute(name, arguments)
