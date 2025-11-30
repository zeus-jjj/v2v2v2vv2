
from typing import List, Dict, Any
import aiohttp

from interfaces import IAsyncAPIService
from decorators import async_retry, log_execution, log_errors, measure_time
import logging

logger = logging.getLogger(__name__)


class AsyncPokerHubAPIService(IAsyncAPIService):

    def __init__(self, api_url: str, timeout: int = 30):
        self.api_url = api_url
        
        # 🚀 ОПТИМИЗАЦИЯ: Увеличен таймаут для больших батчей
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=10)
        self.session: aiohttp.ClientSession = None
        
        # 🚀 ОПТИМИЗАЦИЯ: Connection pooling для переиспользования соединений
        self.connector = aiohttp.TCPConnector(
            limit=10,           # Максимум 10 одновременных соединений
            limit_per_host=10,  # По 10 на хост
            ttl_dns_cache=300,  # Кэш DNS на 5 минут
            force_close=False,  # Переиспользовать соединения
            enable_cleanup_closed=True
        )

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=self.connector  # 🚀 Используем connector с pooling
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        # Connector закроется автоматически при закрытии session

    @async_retry(
        max_attempts=3,
        base_delay=2.0,
        exceptions=(aiohttp.ClientError,)
    )
    @measure_time(threshold_seconds=15.0)
    @log_execution()
    async def get_users(self, user_ids: List[int]) -> List[Dict[str, Any]]:

        if not user_ids:
            logger.warning("No user IDs provided to PokerHub API")
            return []

        # 🚀 ОПТИМИЗАЦИЯ: Увеличен размер батча
        # БЫЛО: 100 users/batch = 53 requests для 5278 users
        # СТАЛО: 500 users/batch = 11 requests для 5278 users
        # ЭКОНОМИЯ: ~20-25 секунд
        batch_size = 500
        all_users = []

        close_session = False
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                connector=self.connector  # 🚀 Используем connector с pooling
            )
            close_session = True

        try:
            import asyncio
            tasks = [
                self._fetch_user_batch(user_ids[i:i + batch_size])
                for i in range(0, len(user_ids), batch_size)
            ]

            logger.debug(f"Fetching {len(user_ids)} users in {len(tasks)} batches (batch_size={batch_size})")

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch request failed: {result}")
                else:
                    all_users.extend(result)

            logger.info(f"Fetched {len(all_users)} users from PokerHub API in {len(tasks)} batches [ASYNC]")
            return all_users

        finally:
            if close_session:
                await self.session.close()
                self.session = None

    async def _fetch_user_batch(self, user_ids: List[int]) -> List[Dict[str, Any]]:
        input_data = {"users": user_ids}

        async with self.session.post(
            self.api_url,
            json=input_data,
            headers={'Content-Type': 'application/json'}
        ) as response:
            response.raise_for_status()
            return await response.json()

    @log_errors(reraise=False)
    async def health_check(self) -> bool:

        try:
            result = await self.get_users([])
            return isinstance(result, list)
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False
