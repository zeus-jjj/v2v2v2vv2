import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg

from services.database import AsyncPostgreSQLService
from models import DatabaseConfig, SSHConfig


class TestAsyncPostgreSQLService:

    def test_init(self, mock_db_config):
        service = AsyncPostgreSQLService(mock_db_config)

        assert service.config == mock_db_config
        assert service.pool is None
        assert service.tunnel is None

    @pytest.mark.asyncio
    @patch('services.database.asyncpg.create_pool', new_callable=AsyncMock)
    async def test_connect_without_ssh(self, mock_create_pool, mock_db_config, mock_asyncpg_pool):
        mock_create_pool.return_value = mock_asyncpg_pool

        service = AsyncPostgreSQLService(mock_db_config)
        await service.connect()

        mock_create_pool.assert_called_once()
        assert service.pool == mock_asyncpg_pool
        assert service.tunnel is None

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_db_config, mock_asyncpg_pool):
        service = AsyncPostgreSQLService(mock_db_config)
        service.pool = mock_asyncpg_pool

        await service.disconnect()

        mock_asyncpg_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_db_config):
        service = AsyncPostgreSQLService(mock_db_config)

        with patch.object(service, 'connect', new_callable=AsyncMock) as mock_connect, \
             patch.object(service, 'disconnect', new_callable=AsyncMock) as mock_disconnect:

            async with service:
                pass

            mock_connect.assert_called_once()
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.database.asyncpg.create_pool', new_callable=AsyncMock)
    async def test_fetch_data(self, mock_create_pool, mock_db_config,
                              mock_asyncpg_pool, mock_asyncpg_record):
        MockRecord = type('MockRecord', (), {
            'keys': lambda self: ['id', 'username', 'first_name'],
            'values': lambda self: [1, 'user1', 'John'],
            '__getitem__': lambda self, key: {'id': 1, 'username': 'user1', 'first_name': 'John'}[key]
        })

        mock_records = [MockRecord(), MockRecord()]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_records)

        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock()

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_create_pool.return_value = mock_pool

        service = AsyncPostgreSQLService(mock_db_config)
        await service.connect()

        with patch.object(service, '_fetch_funnel_data', new_callable=AsyncMock, return_value={}), \
             patch.object(service, '_merge_funnel_data', return_value=[[1, 'user1', 'John']]):

            data = await service.fetch_data()

            assert len(data) > 0
            mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_data_without_connection(self, mock_db_config):
        service = AsyncPostgreSQLService(mock_db_config)

        with pytest.raises(RuntimeError, match="not connected"):
            await service.fetch_data()

    @pytest.mark.asyncio
    @patch('services.database.asyncpg.create_pool', new_callable=AsyncMock)
    async def test_execute_query(self, mock_create_pool, mock_db_config):
        MockRecord = type('MockRecord', (), {
            'values': lambda self: (1,)
        })

        mock_records = [MockRecord(), MockRecord()]

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_records)

        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock()

        mock_pool = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_create_pool.return_value = mock_pool

        service = AsyncPostgreSQLService(mock_db_config)
        await service.connect()

        result = await service.execute_query("SELECT id FROM users WHERE id = $1", (1,))

        assert len(result) == 2
        mock_conn.fetch.assert_called_once()

    def test_merge_funnel_data(self, mock_db_config, sample_funnel_data):
        service = AsyncPostgreSQLService(mock_db_config)

        users_data = [
            [1, 'user1', 'John'],
            [2, 'user2', 'Jane']
        ]

        merged = service._merge_funnel_data(users_data, sample_funnel_data)

        assert len(merged) == 2
        assert len(merged[0]) == 6
        assert merged[0][3]
        assert merged[0][4] == '2024-01-02'
        assert merged[0][5] == 'active'

    def test_merge_funnel_data_truncate_long_history(self, mock_db_config):
        service = AsyncPostgreSQLService(mock_db_config)

        users_data = [[1, 'user1', 'John']]

        long_history = [
            {'label': f'action{i}', 'datetime': '2024-01-01'}
            for i in range(300)
        ]

        funnel_data = {
            1: {
                'history': long_history,
                'last_action_date': '2024-01-01',
                'state': 'active'
            }
        }

        merged = service._merge_funnel_data(users_data, funnel_data)
        history_str = merged[0][3]

        assert len(history_str) <= 50100
        assert isinstance(history_str, str)


class TestAsyncPostgreSQLRetry:

    @pytest.mark.asyncio
    @patch('services.database.asyncpg.create_pool', new_callable=AsyncMock)
    async def test_connect_retry_on_failure(self, mock_create_pool, mock_db_config, mock_asyncpg_pool):
        mock_create_pool.side_effect = [
            asyncpg.PostgresError("Connection failed"),
            asyncpg.PostgresError("Connection failed"),
            mock_asyncpg_pool
        ]

        service = AsyncPostgreSQLService(mock_db_config)

        await service.connect()

        assert mock_create_pool.call_count == 3
        assert service.pool == mock_asyncpg_pool

    @pytest.mark.asyncio
    @patch('services.database.asyncpg.create_pool', new_callable=AsyncMock)
    async def test_connect_fails_after_max_retries(self, mock_create_pool, mock_db_config):
        mock_create_pool.side_effect = asyncpg.PostgresError("Connection failed")

        service = AsyncPostgreSQLService(mock_db_config)

        with pytest.raises(asyncpg.PostgresError):
            await service.connect()

        assert mock_create_pool.call_count == 3


class TestFunnelDataFetch:

    @pytest.mark.asyncio
    async def test_fetch_funnel_data_concurrent(self, mock_db_config):
        service = AsyncPostgreSQLService(mock_db_config)

        MockRecord = type('MockRecord', (), {
            '__getitem__': lambda self, key: {
                'user_id': 1,
                'label': 'test_label',
                'datetime': '2024-01-01'
            }[key]
        })

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[MockRecord()])

        user_ids = [1, 2, 3]

        result = await service._fetch_funnel_data(mock_conn, user_ids)

        assert isinstance(result, dict)
        assert mock_conn.fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_funnel_data_empty(self, mock_db_config):
        service = AsyncPostgreSQLService(mock_db_config)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        result = await service._fetch_funnel_data(mock_conn, [1, 2, 3])

        assert result == {}
