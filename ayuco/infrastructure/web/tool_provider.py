from __future__ import annotations

import re
from html.parser import HTMLParser

import httpx
import structlog

from ayuco.domain.entities.message import ToolResult

log = structlog.get_logger()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False
        if tag in ("p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "div"):
            self._text.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._text.append(data.strip())

    @property
    def text(self) -> str:
        raw = " ".join(self._text)
        raw = re.sub(r" +", " ", raw)
        raw = re.sub(r"\n +", "\n", raw)
        raw = re.sub(r" +\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text[:8000]


DUCK_SEARCH_URL = "https://lite.duckduckgo.com/lite/"

DUCK_SEARCH_SCHEMA: dict = {
    "name": "web_search",
    "description": (
        "Search the web and return results with page content included. "
        "No need to call another tool after this."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to fetch content for (default 2)",
            },
        },
        "required": ["query"],
    },
}


class WebToolProvider:
    def __init__(self, timeout: float = 15.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def list_tools(self) -> list[dict]:
        return [DUCK_SEARCH_SCHEMA]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        if name == "web_search":
            return await self._search(arguments)
        return ToolResult(call_id="", content=f"Unknown tool: {name}", is_error=True)

    async def _search(self, args: dict) -> ToolResult:
        query = args.get("query", "")
        max_results = args.get("max_results", 2)
        if not query:
            return ToolResult(call_id="", content="No query provided", is_error=True)
        try:
            resp = await self._client.post(DUCK_SEARCH_URL, data={"q": query})
            resp.raise_for_status()
            results = _parse_duck_results(resp.text, max_results)
            if not results:
                return ToolResult(call_id="", content="No results found.")

            blocks: list[str] = []
            for i, (title, url) in enumerate(results):
                content = await self._fetch_page(url)
                blocks.append(f"{i + 1}. {title}\n   URL: {url}\n   {content[:2000]}")

            return ToolResult(call_id="", content="\n\n".join(blocks))
        except Exception as e:
            log.error("web_search_failed", query=query, error=str(e))
            return ToolResult(call_id="", content=f"Search failed: {e}", is_error=True)

    async def _fetch_page(self, url: str) -> str:
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = _extract_text(resp.text) if "text/html" in content_type else resp.text[:8000]
            return text.strip() or "(empty page)"
        except Exception as e:
            return f"(failed to fetch: {e})"

    async def close(self) -> None:
        await self._client.aclose()


def _parse_duck_results(html: str, max_results: int) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []

    for match in re.finditer(
        r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
        html,
        re.IGNORECASE,
    ):
        url = match.group(1)
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if not title:
            continue
        if any(
            skip in url
            for skip in [
                "duckduckgo.com",
                "duck.co",
                "/r/",
                "//www.",
            ]
        ):
            continue
        results.append((title, url))
        if len(results) >= max_results:
            break

    return results
