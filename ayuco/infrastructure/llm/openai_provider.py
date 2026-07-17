from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from ayuco.domain.entities.message import Message, ToolCall
from ayuco.domain.ports.llm import LLMResponse

log = structlog.get_logger()


def _message_to_dict(msg: Message) -> dict[str, Any]:
    d: dict[str, Any] = {
        "role": msg.role.value,
        "content": None if msg.tool_calls else msg.content,
    }
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in msg.tool_calls
        ]
    if msg.tool_result:
        d["tool_call_id"] = msg.tool_result.call_id
    return d


class OpenAIProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [_message_to_dict(m) for m in messages],
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
            payload["tool_choice"] = "auto"

        resp = await self._client.post("/chat/completions", json=payload)
        if resp.status_code >= 400:
            log.error(
                "llm_request_failed",
                status=resp.status_code,
                body=resp.text,
                model=self._model,
            )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        msg = choice["message"]
        usage = data.get("usage", {})

        tool_calls = tuple(
            ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                arguments=json.loads(tc["function"]["arguments"]),
            )
            for tc in msg.get("tool_calls", [])
        )

        log.debug(
            "llm_response",
            model=self._model,
            tool_calls=len(tool_calls),
            usage=usage,
        )

        return LLMResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            usage=usage,
        )

    async def close(self) -> None:
        await self._client.aclose()
