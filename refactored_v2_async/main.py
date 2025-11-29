
import sys
import asyncio
import logging
from injector import Injector

from models import Settings
from di_container import AsyncApplicationModule
from services import AsyncScheduler


def setup_logging(level: str = "INFO") -> None:

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


async def async_main() -> None:
    try:
        settings = Settings()

        setup_logging(settings.log_level)
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
        logger = logging.getLogger(__name__)
        logger.info("Service interrupted by user")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Service stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
