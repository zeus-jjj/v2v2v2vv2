
from typing import List, Dict, Any
import aiohttp

from interfaces import IAsyncAPIService
from decorators import async_retry, log_execution, log_errors, measure_time
import logging

logger = logging.getLogger(__name__)


class AsyncPokerHubAPIService(IAsyncAPIService):


    def __init__(self, api_url: str, timeout: int = 30):

        self.api_url = api_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @async_retry(
        max_attempts=3,
        base_delay=2.0,
        exceptions=(aiohttp.ClientError,)
    )
    @measure_time(threshold_seconds=5.0)
    @log_execution()
    async def get_users(self, user_ids: List[int]) -> List[Dict[str, Any]]:

        if not user_ids:
            logger.warning("No user IDs provided to PokerHub API")
            return []

        batch_size = 100
        all_users = []

        close_session = False
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            close_session = True

        try:
            import asyncio
            tasks = [
                self._fetch_user_batch(user_ids[i:i + batch_size])
                for i in range(0, len(user_ids), batch_size)
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch request failed: {result}")
                else:
                    all_users.extend(result)

            logger.info(f"Fetched {len(all_users)} users from PokerHub API [ASYNC]")
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
