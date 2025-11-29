from typing import List, Dict, Any, Optional, Union
import platform
import asyncpg
import asyncssh
from sshtunnel import SSHTunnelForwarder

from interfaces import IAsyncDatabaseService
from models import DatabaseConfig
from decorators import async_retry, log_execution, log_errors, measure_time
import logging

logger = logging.getLogger(__name__)


class AsyncPostgreSQLService(IAsyncDatabaseService):

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self.tunnel: Optional[Union[asyncssh.SSHClientConnection, SSHTunnelForwarder]] = None
        self.listener = None
        self.is_async_tunnel: bool = False  # Флаг для определения типа туннеля
        self.local_port: Optional[int] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    @log_execution()
    @async_retry(max_attempts=3, exceptions=(asyncpg.PostgresError,))
    async def connect(self) -> None:
        if self.config.ssh_config:
            await self._setup_ssh_tunnel()
            host = '127.0.0.1'
            port = self.local_port
        else:
            host = self.config.host
            port = self.config.port

        self.pool = await asyncpg.create_pool(
            host=host,
            port=port,
            database=self.config.name,
            user=self.config.user,
            password=self.config.password,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )

        logger.info(f"Connected to database: {self.config.name} ({host}:{port}) [ASYNC POOL]")

    @log_errors()
    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            logger.info(f"Disconnected from database: {self.config.name}")

        # Закрываем listener (только для async tunnel)
        if self.listener:
            self.listener.close()
            await self.listener.wait_closed()

        # Закрываем tunnel (зависит от типа)
        if self.tunnel:
            if self.is_async_tunnel:
                # Async tunnel (Linux/Mac)
                self.tunnel.close()
                await self.tunnel.wait_closed()
                logger.info(f"Async SSH tunnel stopped for {self.config.name}")
            else:
                # Sync tunnel (Windows)
                self.tunnel.stop()
                logger.info(f"Sync SSH tunnel stopped for {self.config.name}")

    async def _setup_ssh_tunnel(self) -> None:
        ssh_cfg = self.config.ssh_config

        # Определяем ОС и выбираем метод создания туннеля
        if platform.system() == "Windows":
            # ========== WINDOWS: Синхронный SSH tunnel ==========
            logger.info(f"Detected Windows OS. Using synchronous SSH tunnel for {self.config.name}")

            self.tunnel = SSHTunnelForwarder(
                (ssh_cfg.host, ssh_cfg.port),
                ssh_username=ssh_cfg.user,
                ssh_password=ssh_cfg.password,
                remote_bind_address=(self.config.host, self.config.port),
            )
            self.tunnel.start()
            self.local_port = self.tunnel.local_bind_port
            self.is_async_tunnel = False

            logger.info(
                f"Sync SSH tunnel created for {self.config.name}. "
                f"Local port: {self.local_port}"
            )
        else:
            # ========== LINUX/MAC: Асинхронный SSH tunnel ==========
            logger.info(f"Detected {platform.system()} OS. Using async SSH tunnel for {self.config.name}")

            self.tunnel = await asyncssh.connect(
                ssh_cfg.host,
                port=ssh_cfg.port,
                username=ssh_cfg.user,
                password=ssh_cfg.password,
                known_hosts=None,
            )

            self.listener = await self.tunnel.forward_local_port(
                '127.0.0.1',
                0,
                self.config.host,
                self.config.port
            )

            self.local_port = self.listener.get_port()
            self.is_async_tunnel = True

            logger.info(
                f"Async SSH tunnel created for {self.config.name}. "
                f"Local port: {self.local_port} [ASYNC]"
            )

    @measure_time(threshold_seconds=10.0)
    @log_errors()
    async def fetch_data(self) -> List[List[Any]]:
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(self.config.query)

            if not rows:
                return []

            columns = list(rows[0].keys())

            logger.info(f"Fetched {len(rows)} rows from {self.config.name} [ASYNC]")

            users_data = [list(dict(r).values()) for r in rows]

            user_ids = [row[0] for row in users_data if row and row[0] is not None]

            if not user_ids:
                logger.warning("No user IDs for funnel history query")
                return [columns] + users_data

            funnel_data = await self._fetch_funnel_data(conn, user_ids)
            merged_data = self._merge_funnel_data(users_data, funnel_data)

            headers = columns + ['funnel_history', 'last_action_date', 'max_funnel_action']
            return [headers] + merged_data

    @async_retry(max_attempts=2, exceptions=(asyncpg.PostgresError,))
    async def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or ()))
            return [tuple(r.values()) for r in rows]

    async def _fetch_funnel_data(self, conn, user_ids: List[int]) -> Dict[int, Dict]:
        import asyncio

        history_task = conn.fetch(
            """
            SELECT user_id, label, datetime
            FROM funnel_history
            WHERE user_id = ANY($1::int[])
            ORDER BY user_id, datetime
            """,
            user_ids
        )

        state_task = conn.fetch(
            """
            SELECT DISTINCT ON (user_id) user_id, label
            FROM user_funnel
            WHERE user_id = ANY($1::int[])
            ORDER BY user_id, datetime DESC
            """,
            user_ids
        )

        history_rows, state_rows = await asyncio.gather(history_task, state_task)

        funnel_data = {}

        for row in history_rows:
            user_id = row['user_id']
            if user_id not in funnel_data:
                funnel_data[user_id] = {
                    'history': [],
                    'last_action_date': '',
                    'state': ''
                }

            funnel_data[user_id]['history'].append({
                'label': row['label'],
                'datetime': row['datetime']
            })
            funnel_data[user_id]['last_action_date'] = row['datetime']

        for row in state_rows:
            user_id = row['user_id']
            if user_id in funnel_data:
                funnel_data[user_id]['state'] = row['label']
            else:
                funnel_data[user_id] = {
                    'history': [],
                    'last_action_date': '',
                    'state': row['label']
                }

        return funnel_data

    def _merge_funnel_data(
        self,
        users_data: List[List[Any]],
        funnel_data: Dict[int, Dict]
    ) -> List[List[Any]]:
        merged_data = []

        for row in users_data:
            user_id = int(row[0])
            user_funnel = funnel_data.get(user_id, {
                'history': [],
                'last_action_date': '',
                'state': ''
            })

            history_parts = [
                f"[{h['datetime']} - {h['label']}]"
                for h in user_funnel['history']
            ]
            history_str = "\n".join(history_parts) if history_parts else ""

            if len(history_str) > 40_000:
                if len(history_parts) > 200:
                    history_str = (
                        "\n".join(history_parts[:100]) +
                        f"\n[...{len(history_parts)-200} entries...]" +
                        "\n".join(history_parts[-100:])
                    )
                else:
                    history_str = history_str[:40_000] + "\n[TRUNCATED]"

            merged_row = row + [
                history_str,
                user_funnel['last_action_date'],
                user_funnel['state']
            ]
            merged_data.append(merged_row)

        return merged_data
