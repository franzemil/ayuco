from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("ayuco.json")


def load_config(path: Path | str | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        print(
            f"Copy config.example.json to {config_path} and fill in your settings.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(config_path) as f:
        config = json.load(f)
    _validate(config)
    return config


def _validate(config: dict) -> None:
    required = ["telegram", "llm", "storage"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")
    if "token" not in config["telegram"]:
        raise ValueError("Missing telegram.token")
    for k in ("base_url", "api_key", "model"):
        if k not in config["llm"]:
            raise ValueError(f"Missing llm.{k}")
    config.setdefault("storage", {}).setdefault("db_path", "ayuco.db")
    config.setdefault("memory", {})
    config["memory"].setdefault("mode", "sliding")
    config["memory"].setdefault("max_messages", 40)
    config["memory"].setdefault("summarize_threshold", 100)
    config.setdefault("sandbox", {})
    config["sandbox"].setdefault("enabled", True)
    config["sandbox"].setdefault("engine", "bwrap")
    config["sandbox"].setdefault("bwrap_path", "/usr/bin/bwrap")
    config["sandbox"].setdefault("timeout", 30)
    config["sandbox"].setdefault("allowed_commands", [])
    config.setdefault("mcp", {})
    config["mcp"].setdefault("servers", [])
    config["llm"].setdefault("system_prompt", "You are a helpful assistant.")
