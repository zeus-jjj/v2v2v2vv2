import asyncio
import random
import logging
import signal
from typing import List, Dict, Any, Callable, Optional, Set
from injector import inject

from models import Settings, DatabaseConfig
from interfaces import IAsyncSheetsService, IAsyncAPIService, IParser, IAsyncDatabaseService
from config import DatabaseConfigFactory
from decorators import log_execution, log_errors, measure_time
from utils.helpers import make_status_line, get_column_index, get_column_range_end, parse_to_gs_date

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Simple health check service for monitoring"""

    def __init__(self):
        from datetime import datetime
        self.last_update: Optional[datetime] = None
        self.update_count: int = 0
        self.error_count: int = 0
        self.is_healthy: bool = True

    def record_update_start(self) -> None:
        """Record start of update cycle"""
        from datetime import datetime
        self.last_update = datetime.now()

    def record_update_success(self) -> None:
        """Record successful update"""
        self.update_count += 1
        self.is_healthy = True

    def record_error(self) -> None:
        """Record error"""
        self.error_count += 1

    def get_status(self) -> Dict[str, Any]:
        """Get current health status"""
        from datetime import datetime
        return {
            "status": "healthy" if self.is_healthy else "unhealthy",
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "uptime": (datetime.now() - self.last_update).total_seconds()
                      if self.last_update else 0
        }


class AsyncScheduler:

    @inject
    def __init__(
        self,
        settings: Settings,
        sheets_service: IAsyncSheetsService,
        api_service: IAsyncAPIService,
        parser: IParser,
        db_factory: DatabaseConfigFactory,
        db_service_factory: Callable[[DatabaseConfig], IAsyncDatabaseService]
    ):
        self.settings = settings
        self.sheets_service = sheets_service
        self.api_service = api_service
        self.parser = parser
        self.db_factory = db_factory
        self.db_service_factory = db_service_factory
        self.db_configs: List[DatabaseConfig] = []

        # Graceful shutdown support
        self._shutdown_event = asyncio.Event()
        self._running_tasks: Set[asyncio.Task] = set()

        # Health check
        self.health_check = HealthCheckService()

    @log_execution()
    async def run(self) -> None:
        logger.info("=" * 80)
        logger.info("Service started (FULLY ASYNC MODE)")
        logger.info("=" * 80)

        self.db_configs = self.db_factory.create_all_configs()
        logger.info(f"Loaded {len(self.db_configs)} database configurations")

        await self.sheets_service.connect()

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        logger.info("Performing initial update (CONCURRENT)...")
        await self.update_all_sheets()
        logger.info("Initial update completed")

        logger.info(
            f"Entering update loop. Interval: {self.settings.update_interval_minutes} minutes..."
        )

        # Main loop with graceful shutdown support
        while not self._shutdown_event.is_set():
            try:
                # Wait for either timeout or shutdown signal
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.settings.update_interval_minutes * 60
                )
            except asyncio.TimeoutError:
                # Timeout reached - time to update
                if not self._shutdown_event.is_set():
                    await self.update_all_sheets()

        logger.info("Scheduler stopped gracefully ✅")

    def _setup_signal_handlers(self) -> None:
        """Setup handlers for graceful shutdown"""
        try:
            # Try to setup signal handlers (works on Unix-like systems)
            loop = asyncio.get_running_loop()

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_shutdown(s))
                )

            logger.info("Signal handlers configured (Unix)")
        except (NotImplementedError, AttributeError):
            # Windows doesn't support add_signal_handler
            logger.warning(
                "Signal handlers not supported on this platform (Windows). "
                "Use Ctrl+C for shutdown."
            )

    async def _handle_shutdown(self, sig: signal.Signals) -> None:
        """Handle shutdown signal"""
        logger.info("=" * 80)
        logger.info(f"Received signal {sig.name}. Initiating graceful shutdown...")
        logger.info("=" * 80)

        # Set shutdown flag
        self._shutdown_event.set()

        # Wait for running tasks to complete
        if self._running_tasks:
            logger.info(f"Waiting for {len(self._running_tasks)} tasks to complete...")
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            logger.info("All tasks completed")

        logger.info("Shutdown complete ✅")

    @measure_time(threshold_seconds=60.0)
    @log_execution()
    async def update_all_sheets(self) -> None:
        # Record update start for health check
        self.health_check.record_update_start()

        logger.info(f"Starting CONCURRENT update of {len(self.db_configs)} sheets...")

        tasks = [
            self._update_single_sheet(config)
            for config in self.db_configs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        error_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                self.health_check.record_error()
                config = self.db_configs[i]
                logger.error(
                    f"Error updating {config.name} -> '{config.sheet_tab_name}': {result}"
                )

        # Record success if no errors
        if error_count == 0:
            self.health_check.record_update_success()
            logger.info(f"All {len(self.db_configs)} sheets updated (CONCURRENT) ✅")
        else:
            logger.warning(
                f"Update completed with {error_count}/{len(self.db_configs)} errors ⚠️"
            )

    @measure_time(threshold_seconds=30.0)
    @log_errors()
    async def _update_single_sheet(self, config: DatabaseConfig) -> None:
        tab = config.sheet_tab_name

        logger.info(f"Updating '{tab}'...")

        async with self.db_service_factory(config) as db:
            data = await db.fetch_data()

        if not data:
            headers = []
            user_data = []
        else:
            headers = data[0]
            user_data = data[1:]

        if config.use_pokerhub_data and user_data:
            user_data, headers = await self._integrate_pokerhub_data(
                user_data,
                headers,
                config
            )

        data = [headers] + user_data

        await self.sheets_service.update_sheet(
            tab_name=tab,
            data=data,
            start_row=config.start_row,
            column_range=config.column_range,
            clear_tail=not config.clear_on_empty
        )

        status = make_status_line(tab, len(user_data))
        await self.sheets_service.update_status(tab, status)

        logger.info(f"✓ Updated: {config.name} -> '{tab}', rows: {len(user_data)}")

        await asyncio.sleep(0.1 + random.uniform(0, 0.2))

    async def _integrate_pokerhub_data(
        self,
        user_data: List[List[Any]],
        headers: List[str],
        config: DatabaseConfig
    ) -> tuple[List[List[Any]], List[str]]:
        logger.info("Fetching PokerHub data (ASYNC)...")

        user_ids = [row[0] for row in user_data if row and row[0] is not None]

        if not user_ids:
            logger.warning("No user IDs for PokerHub API")
            return user_data, headers

        ph_users_raw = await self.api_service.get_users(user_ids)

        if not ph_users_raw:
            logger.warning("No data from PokerHub API")
            return user_data, headers

        ph_users_dict = {
            int(user['tg_id']): user
            for user in ph_users_raw
            if 'tg_id' in user
        }

        logger.info(f"Received {len(ph_users_dict)} users from PokerHub API")

        merged_headers = headers + [
            'ph_utm_medium', 'ph_utm_source', 'ph_utm_campaign',
            'ph_referer', 'auth_date', 'last_visit',
            'group', 'courses', 'lessons',
            'last_action_date', 'max_funnel_action'
        ]

        merged_user_data = []

        for row in user_data:
            user_id = row[0]
            ph_user_data = ph_users_dict.get(int(user_id), {})

            ph_utm = ph_user_data.get("utm") or {}
            merged_row = self._build_merged_row(row, ph_user_data, ph_utm, config)
            merged_user_data.append(merged_row)

        logger.info(f"Data merged. Total rows: {len(merged_user_data)}")

        return merged_user_data, merged_headers

    def _build_merged_row(
        self,
        row: List[Any],
        ph_user_data: Dict,
        ph_utm: Dict,
        config: DatabaseConfig
    ) -> List[Any]:
        utm_medium = ph_utm.get("utm_medium", '')
        utm_source = ph_utm.get("utm_source", '')
        utm_campaign = ph_utm.get("utm_campaign", '')
        referer = ph_user_data.get("referer", '')
        auth_date = parse_to_gs_date(ph_user_data.get('authorization_date', ''))
        last_visit = parse_to_gs_date(ph_user_data.get('last_visit_date', ''))

        all_data = []

        if ph_user_data.get('courses'):
            courses_data = ph_user_data['courses']
            if isinstance(courses_data, dict):
                all_data.append(courses_data)

        if ph_user_data.get('lessons'):
            lessons_data = ph_user_data['lessons']
            if isinstance(lessons_data, list):
                all_data.extend(lessons_data)
            else:
                all_data.append(lessons_data)

        if ph_user_data.get('group'):
            group_data = ph_user_data['group']
            if isinstance(group_data, list):
                all_data.extend(group_data)
            else:
                all_data.append(group_data)

        courses, lessons = self.parser.parse(all_data)

        group_items = ph_user_data.get('group', [])
        if isinstance(group_items, list):
            group_filtered = [
                g for g in group_items
                if isinstance(g, str) and not ('Модуль' in g and 'Урок' in g)
            ]
            group = "\n".join(group_filtered)
        else:
            group = str(group_items) if group_items else ''

        user_last_action_datetime = parse_to_gs_date(
            row[-2].strftime('%Y-%m-%d %H:%M:%S')
        ) if row[-2] else ""
        user_last_funnel_state = row[-1] or ""

        new_row = row[:-2] + [
            utm_medium, utm_source, utm_campaign, referer,
            auth_date, last_visit, group, courses, lessons,
            user_last_action_datetime, user_last_funnel_state
        ]

        end_col_letter = get_column_range_end(config.column_range)
        end_col_index = get_column_index(end_col_letter)
        current_len = len(new_row)

        if current_len < end_col_index:
            new_row += [''] * (end_col_index - current_len)
        elif current_len > end_col_index:
            new_row = new_row[:end_col_index]

        return new_row
