# AGENTS.md

## Commands

- **Install deps:** `uv sync`
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`
- **Run (Telegram):** `uv run python main.py --config ayuco.json`
- **Run (CLI):** `uv run python main.py --cli`
- **Check formatting:** `uv run ruff format . --check`

No test suite exists yet — ignore `pytest` commands if encountered.

## Project Structure (Clean Architecture)

```
ayuco/
  domain/          ← pure logic, no framework deps
    entities/        ← dataclasses: Message, Role, ToolCall, ToolResult
    ports/           ← ABC interfaces: Channel, LLM, Memory, Repository, ToolProvider
    use_cases/       ← HandleMessage (core agent loop)
  infrastructure/  ← concrete implementations
    llm/             ← OpenAIProvider (httpx-based, OpenAI-compatible API)
    memory/          ← SlidingWindowMemory, SummarizedMemory
    persistence/     ← SQLiteMessageRepository (aiosqlite)
    sandbox/         ← BwrapExecutor, SandboxToolProvider
    mcp/             ← MCPToolProvider (mcp SDK, stdio transport)
  adapters/        ← UI entry points
    telegram/        ← TelegramChannel (python-telegram-bot)
    cli.py           ← CLIBot (stdin/stdout)
  config.py        ← pydantic-settings Settings (JSON + env var overrides)
  composition.py   ← build() DI wiring function
  logging.py       ← setup_logging() structlog config
```

## Conventions

- **Python 3.12+** — use `from __future__ import annotations` in every module.
- **All config** via `pydantic-settings` in `ayuco/config.py`. Env vars override JSON config; prefix `AYUCO_`, nested delimiter `__`.
- **Logging:** `structlog` only — never stdlib `logging.getLogger(__name__)`. Use `structlog.get_logger()`.
- **Entities:** frozen `@dataclass`, not Pydantic models.
- **Ports:** ABC-based, defined in `domain/ports/`.
- **Ruff rules:** E, F, I, N, W, UP, B, SIM, RUF, PTH. No comments (ruff D not enforced, but avoid them).
- **Linter command:** always `uv run ruff check .` and `uv run ruff format . --check` after edits.

## Key Quirks

- `config.json` is gitignored (secrets). `config.example.json` is the committed reference.
- `Settings.__init__` loads `ayuco.json` (or `AYUCO_CONFIG_PATH`) and deep-merges with kwargs before calling `super().__init__()`.
- `settings_customise_sources` returns `(env_settings, init_settings)` — no dotenv support.
- Sandbox: `bwrap` command whitelist enforced; falls back to plain subprocess if bwrap missing. `MAX_TOOL_ROUNDS = 5` caps agent loop iterations.
- MCP tools are prefixed `mcp_{server_name}_` when registered.
- Memory mode `"summarized"` requires LLM calls for summarization; `"sliding"` is pure truncation.
