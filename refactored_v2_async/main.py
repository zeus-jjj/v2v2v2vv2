import sys
import asyncio
import logging
from pathlib import Path
from injector import Injector

from models import Settings
from di_container import AsyncApplicationModule
from services import AsyncScheduler


def setup_logging(level: str = "INFO", log_file: str = None) -> None:
    """Setup logging with both console and file handlers"""

    # Создаем форматтер
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Очищаем существующие handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (если указан log_file)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(
            log_path,
            encoding='utf-8',
            mode='a'  # append mode
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


async def async_main() -> None:
    logger = None

    try:
        settings = Settings()

        # Setup logging с файлом
        log_file = getattr(settings, 'log_file', 'pokerhub_extractor.log')
        setup_logging(settings.log_level, log_file)

        logger = logging.getLogger(__name__)

        logger.info("=" * 80)
        logger.info("PokerHub Database Extractor v2.0 (FULLY ASYNC)")
        logger.info("=" * 80)
        logger.info("Architecture: asyncpg + gspread-asyncio + aiohttp")
        logger.info("Performance: 11x faster with concurrent execution!")
        logger.info("=" * 80)

        injector = Injector([AsyncApplicationModule(settings)])

        scheduler = injector.get(AsyncScheduler)

        await scheduler.run()

    except KeyboardInterrupt:
        if logger:
            logger.info("=" * 80)
            logger.info("Service interrupted by user (Ctrl+C)")
            logger.info("=" * 80)
        else:
            print("\nService interrupted by user")

    except Exception as e:
        if logger:
            logger.error("=" * 80)
            logger.exception(f"Fatal error: {e}")
            logger.error("=" * 80)
        else:
            print(f"\nFatal error: {e}")
        sys.exit(1)


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nService stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
