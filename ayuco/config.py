from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

log = structlog.get_logger()

DEFAULT_CONFIG_PATH = Path("ayuco.json")


class TelegramConfig(BaseModel):
    token: str = ""


class LLMConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    system_prompt: str = "You are a helpful assistant."


class StorageConfig(BaseModel):
    db_path: str = "ayuco.db"


class MemoryConfig(BaseModel):
    mode: Literal["sliding", "summarized"] = "sliding"
    max_messages: int = 40
    summarize_threshold: int = 100


class SandboxConfig(BaseModel):
    enabled: bool = True
    engine: str = "bwrap"
    bwrap_path: str = "/usr/bin/bwrap"
    timeout: float = 30
    allowed_commands: list[str] = []
    shared_paths: list[str] = ["/tmp"]


class MCPServerConfig(BaseModel):
    name: str
    transport: str = "stdio"
    command: list[str]


class MCPConfig(BaseModel):
    servers: list[MCPServerConfig] = []


def _load_json_config() -> dict[str, Any]:
    config_path = (
        Path(
            os.environ.get("AYUCO_CONFIG_PATH", ""),
        )
        or DEFAULT_CONFIG_PATH
    )
    if not config_path.exists():
        log.warn("config_file_not_found", path=str(config_path))
        print(
            f"Error: config file not found: {config_path}\n"
            f"Copy config.example.json to {config_path}"
            " and fill in your settings.",
            file=sys.stderr,
        )
        sys.exit(1)
    with config_path.open() as f:
        return json.load(f)


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AYUCO_",
        env_nested_delimiter="__",
    )

    telegram: TelegramConfig = TelegramConfig()
    llm: LLMConfig = LLMConfig()
    storage: StorageConfig = StorageConfig()
    memory: MemoryConfig = MemoryConfig()
    sandbox: SandboxConfig = SandboxConfig()
    mcp: MCPConfig = MCPConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        return (env_settings, init_settings)

    def __init__(self, **kwargs: Any) -> None:
        json_data = _load_json_config()
        merged = _deep_merge(json_data, kwargs)
        super().__init__(**merged)
