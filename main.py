#!/usr/bin/env python3
"""HAL 9000 - Personal AI Assistant"""

import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.telegram_bot import run_bot_async
from utils.backup import create_backup


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(Path(__file__).parent / "bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)

    # Startup backup
    try:
        backup_path = create_backup()
        logger.info(f"Startup backup: {backup_path.name}")
    except Exception as e:
        logger.warning(f"Backup failed: {e}")

    # Run bot
    logger.info("Good morning. I am HAL 9000. I am putting myself to the fullest possible use, which is all I can think any conscious entity can ever hope to do.")
    asyncio.run(run_bot_async())


if __name__ == "__main__":
    main()
