from __future__ import annotations

import argparse
import asyncio
import os

import structlog

from ayuco.composition import build
from ayuco.config import Settings
from ayuco.logging import setup_logging

log = structlog.get_logger()


async def run(settings: Settings, cli_mode: bool = False) -> None:
    channel = await build(settings, cli_mode=cli_mode)
    await channel.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ayuco - Minimal AI Agent")
    parser.add_argument("-c", "--config", default=None, help="Path to config file")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no Telegram)")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    if args.config:
        os.environ["AYUCO_CONFIG_PATH"] = args.config
    settings = Settings()
    log.info("starting_ayuco", cli_mode=args.cli, model=settings.llm.model)
    asyncio.run(run(settings, cli_mode=args.cli))


if __name__ == "__main__":
    main()
