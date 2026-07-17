from __future__ import annotations

import asyncio
import shutil

import structlog

from ayuco.domain.entities.message import ToolResult

log = structlog.get_logger()


class BwrapExecutor:
    def __init__(
        self,
        bwrap_path: str = "/usr/bin/bwrap",
        timeout: float = 30.0,
        allowed_commands: list[str] | None = None,
        shared_paths: list[str] | None = None,
    ) -> None:
        self._bwrap = bwrap_path
        self._timeout = timeout
        self._allowed = set(allowed_commands) if allowed_commands else None
        self._shared_paths = shared_paths or []

    async def execute(self, command: str, arguments: dict) -> ToolResult:
        cmd_str = arguments.get("command", command)
        cmd_parts = cmd_str.split()

        if self._allowed and cmd_parts and cmd_parts[0] not in self._allowed:
            return ToolResult(
                call_id="",
                content=f"Command not allowed: {cmd_parts[0]}",
                is_error=True,
            )

        if shutil.which(self._bwrap):
            return await self._run_bwrap(cmd_parts)
        return await self._run_subprocess(cmd_parts)

    async def _run_bwrap(self, cmd_parts: list[str]) -> ToolResult:
        shared = set(self._shared_paths)
        tmp_mount = ["--bind", "/tmp", "/tmp"] if "/tmp" in shared else ["--tmpfs", "/tmp"]
        extra_binds: list[str] = []
        for p in shared:
            if p != "/tmp":
                extra_binds.extend(["--bind", p, p])
        bwrap_cmd = [
            self._bwrap,
            "--ro-bind",
            "/",
            "/",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            *tmp_mount,
            *extra_binds,
            "--unshare-net",
            "--die-with-parent",
            "--",
            *cmd_parts,
        ]
        return await self._run_cmd(bwrap_cmd)

    async def _run_subprocess(self, cmd_parts: list[str]) -> ToolResult:
        log.warning("bwrap_not_found_fallback")
        return await self._run_cmd(cmd_parts)

    async def _run_cmd(self, cmd: list[str]) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
            output = stdout.decode(errors="replace")
            err = stderr.decode(errors="replace")
            if proc.returncode != 0:
                return ToolResult(
                    call_id="",
                    content=f"Exit {proc.returncode}\n{err or output}",
                    is_error=True,
                )
            return ToolResult(call_id="", content=output or err or "(no output)")
        except TimeoutError:
            return ToolResult(
                call_id="",
                content=f"Command timed out after {self._timeout}s",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(call_id="", content=str(e), is_error=True)
