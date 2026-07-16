from __future__ import annotations

import argparse
import asyncio
import logging

from ayuco.composition import build
from ayuco.config import load_config


async def run(config: dict, cli_mode: bool = False) -> None:
    channel = await build(config, cli_mode=cli_mode)
    await channel.run()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Ayuco - Minimal AI Agent")
    parser.add_argument("-c", "--config", default=None, help="Path to config file")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no Telegram)")
    args = parser.parse_args()

    config = load_config(args.config)
    asyncio.run(run(config, cli_mode=args.cli))


if __name__ == "__main__":
    main()
