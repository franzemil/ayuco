from __future__ import annotations

from typing import Protocol, runtime_checkable

from ayuco.domain.entities.message import ToolResult


@runtime_checkable
class ToolProvider(Protocol):
    async def list_tools(self) -> list[dict]: ...

    async def execute(self, name: str, arguments: dict) -> ToolResult: ...
