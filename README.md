# Ayuco

Minimal AI agent. Telegram in, Telegram out. SQLite memory. Sandbox execution. MCP tools. Single process, zero infrastructure.

Built with [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) — domain logic has zero framework dependencies.

## Quick Start

**Linux (one-liner):**

```bash
curl -sSf https://raw.githubusercontent.com/franzemil/ayuco/main/install.sh | bash
```

This installs [uv](https://docs.astral.sh/uv/), [bubblewrap](https://github.com/containers/bubblewrap) (sandbox), clones the repo to `~/.ayuco/`, and sets up dependencies.

**Manual install:**

```bash
git clone https://github.com/franzemil/ayuco.git && cd ayuco
uv sync

# Configure
cp config.example.json ayuco.json
# Edit ayuco.json — add your Telegram token and LLM API key

# Run (Telegram mode)
uv run python main.py

# Or run in CLI mode (no Telegram needed)
uv run python main.py --cli
```

## Configuration

Ayuco is configured via a JSON file (`ayuco.json` by default). Every field can be overridden by environment variables using the `AYUCO_` prefix with `__` as the nested delimiter.

### Config File

```json
{
  "telegram": {
    "token": "YOUR_BOT_TOKEN_HERE"
  },
  "llm": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "model": "gpt-4o-mini",
    "system_prompt": "You are a helpful assistant called Ayuco."
  },
  "storage": {
    "db_path": "ayuco.db"
  },
  "memory": {
    "mode": "sliding",
    "max_messages": 40,
    "summarize_threshold": 100
  },
  "sandbox": {
    "enabled": true,
    "engine": "bwrap",
    "bwrap_path": "/usr/bin/bwrap",
    "timeout": 30,
    "allowed_commands": ["ls", "cat", "grep", "find", "python3", "curl", "echo"]
  },
  "mcp": {
    "servers": [
      {
        "name": "filesystem",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
      }
    ]
  }
}
```

### Environment Variable Overrides

| Env Var | Overrides |
|---|---|
| `AYUCO_CONFIG_PATH` | Path to config file (default: `ayuco.json`) |
| `AYUCO_TELEGRAM__TOKEN` | `telegram.token` |
| `AYUCO_LLM__API_KEY` | `llm.api_key` |
| `AYUCO_LLM__MODEL` | `llm.model` |
| `AYUCO_LLM__BASE_URL` | `llm.base_url` |
| `AYUCO_STORAGE__DB_PATH` | `storage.db_path` |
| `AYUCO_MEMORY__MODE` | `memory.mode` |
| `AYUCO_SANDBOX__ENABLED` | `sandbox.enabled` |
| `AYUCO_SANDBOX__TIMEOUT` | `sandbox.timeout` |

Example: override the model at runtime:

```bash
AYUCO_LLM__MODEL=claude-sonnet-4-20250514 uv run python main.py
```

### Config Priority

Environment variables > config file > defaults.

### CLI Options

```
usage: main.py [-h] [-c CONFIG] [--cli] [--log-level {DEBUG,INFO,WARNING,ERROR}]

options:
  -c, --config      Path to config file
  --cli             Run in CLI mode (no Telegram)
  --log-level       Log verbosity (default: INFO)
```

## Architecture

Ayuco follows Clean Architecture with three layers. Dependencies point inward only.

```
ayuco/
├── domain/                         # ZERO external dependencies
│   ├── entities/                   # Core data types (frozen dataclasses)
│   │   └── message.py             # Message, Role, ToolCall, ToolResult
│   ├── ports/                      # Protocol interfaces
│   │   ├── repository.py          # MessageRepository
│   │   ├── llm.py                 # LLMProvider + LLMResponse
│   │   ├── memory.py              # MemoryManager
│   │   ├── channel.py             # Channel (send + start + run)
│   │   └── tool_provider.py       # ToolProvider (unifies MCP + sandbox)
│   └── use_cases/                  # Application logic
│       ├── handle_message.py      # Core loop: msg → context → LLM → tools → reply
│       ├── execute_tool.py        # Routes tool calls to correct provider
│       └── load_context.py        # Delegates to MemoryManager
│
├── infrastructure/                 # Concrete implementations of ports
│   ├── persistence/               # SQLite (aiosqlite, WAL mode)
│   ├── llm/                       # OpenAI-compatible API (httpx)
│   ├── memory/                    # SlidingWindow + SummarizedMemory
│   ├── sandbox/                   # bwrap executor + ToolProvider wrapper
│   └── mcp/                       # MCP client (mcp SDK v1.x)
│
├── adapters/                       # Entry points (Telegram, CLI)
│   ├── telegram/bot.py
│   └── cli.py
│
├── composition.py                  # Wires everything together
├── config.py                       # pydantic-settings config
├── logging.py                      # structlog setup
└── main.py                         # Entry point
```

### Dependency Rule

```
adapters/ ──→ application/ ──→ domain/
   ↑               ↑
infrastructure/ ───┘
```

- **Domain**: Pure Python. No imports from infrastructure, adapters, or frameworks.
- **Infrastructure**: Implements `Protocol` interfaces from domain/ports. Knows about SQLite, httpx, bwrap, MCP.
- **Adapters**: Translates external world (Telegram updates, CLI input) into domain calls.
- **Composition**: The one place that imports concrete types and wires them together.

### Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Interfaces | `Protocol` (PEP 544) | Structural typing, zero coupling, testable with duck-typed fakes |
| DI | Constructor injection | No framework, no magic, explicit wiring |
| Entities | Frozen dataclasses | Immutable, hashable, no ORM contamination |
| Tool unification | Single `ToolProvider` protocol | MCP tools and sandbox commands are both "tools" to the LLM |
| Memory | Strategy pattern | Swap sliding window / summarized without touching use cases |
| Logging | structlog | Structured key-value output, JSON in production, pretty in dev |
| Config | pydantic-settings | Typed validation, env var overrides, JSON file source |

## LLM Provider

Any OpenAI-compatible API works. Configure `llm.base_url`, `llm.api_key`, and `llm.model`.

| Provider | `base_url` | `model` |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| Anthropic (via proxy) | Your proxy URL | `claude-sonnet-4-20250514` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3`, `mistral` |
| LM Studio (local) | `http://localhost:1234/v1` | Any loaded model |
| OpenRouter | `https://openrouter.ai/api/v1` | Any model |

## Memory

Ayuco stores all messages in SQLite and provides two memory strategies for LLM context.

### Sliding Window (default)

Keeps the last N messages as context. Simple, predictable token usage.

```json
{
  "memory": {
    "mode": "sliding",
    "max_messages": 40
  }
}
```

### Summarized Memory

When message count exceeds `summarize_threshold`, the LLM summarizes older messages into a compact paragraph. The summary is stored in SQLite and prepended to context.

```json
{
  "memory": {
    "mode": "summarized",
    "max_messages": 40,
    "summarize_threshold": 100
  }
}
```

Both modes use SQLite for persistence — conversations survive restarts.

## Sandbox Execution

Commands are executed in a sandboxed environment using [bubblewrap](https://github.com/containers/bubblewrap) (`bwrap`).

### How It Works

1. The LLM receives a `run_command` tool schema
2. LLM calls `run_command` with a shell command
3. Command is checked against the whitelist
4. If whitelisted, executed inside a bwrap sandbox
5. stdout/stderr is captured and returned to the LLM

### Sandbox Flags

| Flag | Effect |
|---|---|
| `--ro-bind / /` | Root filesystem is read-only |
| `--dev /dev` | Minimal /dev |
| `--proc /proc` | Limited /proc visibility |
| `--tmpfs /tmp` | Empty temp dir (clean slate each run) |
| `--unshare-net` | **No network access** |
| `--die-with-parent` | Process dies if ayuco dies |

### Fallback

If `bwrap` is not installed, commands run via plain `subprocess` with a warning. This is less secure but useful for development.

### Configuration

```json
{
  "sandbox": {
    "enabled": true,
    "engine": "bwrap",
    "bwrap_path": "/usr/bin/bwrap",
    "timeout": 30,
    "allowed_commands": ["ls", "cat", "grep", "find", "python3", "curl", "echo"]
  }
}
```

- `allowed_commands`: Only these commands can be executed. Everything else is rejected.
- `timeout`: Maximum seconds per command (default: 30).

## MCP (Model Context Protocol)

Ayuco can connect to external MCP servers to use their tools. Configure servers in the config file:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "filesystem",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
      }
    ]
  }
}
```

MCP tools are prefixed with `mcp_{server_name}_` to avoid name collisions with the sandbox tool.

### Available MCP Servers

Any MCP server that supports stdio transport works. Examples:

- `@modelcontextprotocol/server-filesystem` — File system access
- `@modelcontextprotocol/server-github` — GitHub API
- `@modelcontextprotocol/server-sqlite` — SQLite queries
- `@modelcontextprotocol/server-fetch` — Web fetching

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/clear` | Clear conversation context |
| `/help` | Show help |

Any other text message is processed by the LLM.

## Data Flow

```
User sends Telegram message
  → adapters/telegram/bot.py          (adapter layer)
  → domain/use_cases/handle_message.py (application layer)
    → infrastructure/persistence/      (store inbound)
    → domain/ports/memory.py           (load context)
    → domain/ports/llm.py              (call LLM)
    → domain/ports/tool_provider.py    (execute tools)
      → infrastructure/sandbox/        (bwrap)
      → infrastructure/mcp/            (MCP servers)
    → infrastructure/persistence/      (store outbound)
    → domain/ports/channel.py          (reply)
  → adapters/telegram/bot.py          (send to Telegram)
```

## Dependencies

| Package | Purpose |
|---|---|
| `python-telegram-bot` >=22.8 | Telegram Bot API |
| `httpx` >=0.27 | Async HTTP client for LLM API |
| `aiosqlite` >=0.20 | Async SQLite |
| `mcp` >=1.27,<2 | MCP client SDK |
| `pydantic-settings` >=2.6 | Typed config with env overrides |
| `structlog` >=24.0 | Structured logging |

Dev: `ruff` >=0.8

## Development

```bash
# Install with dev dependencies
uv sync

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Run in CLI mode
uv run python main.py --cli --log-level DEBUG
```

### Linting Rules

Ruff is configured with: `E`, `F`, `I`, `N`, `W`, `UP`, `B`, `SIM`, `RUF`, `PTH`.

## Project Structure

```
ayuco.json           # Your config (not committed)
config.example.json  # Example config
main.py              # Entry point
pyproject.toml       # Project metadata + deps
ayuco/               # Source package
├── domain/          # Core logic (no deps)
├── infrastructure/  # External implementations
├── adapters/        # Telegram + CLI entry points
├── composition.py   # DI wiring
├── config.py        # pydantic-settings
└── logging.py       # structlog setup
```

## License

MIT
