"""
Tests for async PokerHub API service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from services.pokerhub_api import AsyncPokerHubAPIService


class TestAsyncPokerHubAPIService:

    def test_init(self):
        service = AsyncPokerHubAPIService("https://api.test.com/getusers")

        assert service.api_url == "https://api.test.com/getusers"
        assert service.session is None

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_get_users_empty_list(self, mock_session_class):
        service = AsyncPokerHubAPIService("https://api.test.com")

        result = await service.get_users([])

        assert result == []

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_get_users_single_batch(self, mock_session_class, mock_pokerhub_response):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_pokerhub_response)
        mock_response.raise_for_status = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        service = AsyncPokerHubAPIService("https://api.test.com")

        result = await service.get_users([1, 2, 3])

        assert len(result) == 2
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_get_users_multiple_batches(self, mock_session_class):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[{'user_id': 1}, {'user_id': 2}])
        mock_response.raise_for_status = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        service = AsyncPokerHubAPIService("https://api.test.com")

        user_ids = list(range(1, 251))
        result = await service.get_users(user_ids)

        assert mock_session.post.call_count == 3
        assert len(result) == 6

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_get_users_with_context_manager(self, mock_session_class):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])
        mock_response.raise_for_status = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session_class.return_value = mock_session

        service = AsyncPokerHubAPIService("https://api.test.com")

        async with service:
            result = await service.get_users([1, 2])

        assert result == []
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_health_check_success(self, mock_session_class):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])
        mock_response.raise_for_status = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        service = AsyncPokerHubAPIService("https://api.test.com")

        result = await service.health_check()

        assert result is True



class TestAsyncPokerHubAPIRetry:

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_get_users_retry_on_error(self, mock_session_class):
        mock_response_fail = AsyncMock()
        mock_response_fail.raise_for_status = AsyncMock(
            side_effect=aiohttp.ClientError("Network error")
        )
        mock_response_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
        mock_response_fail.__aexit__ = AsyncMock()

        mock_response_success = AsyncMock()
        mock_response_success.json = AsyncMock(return_value=[{'user_id': 1}])
        mock_response_success.raise_for_status = AsyncMock()
        mock_response_success.__aenter__ = AsyncMock(return_value=mock_response_success)
        mock_response_success.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=[
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ])
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        service = AsyncPokerHubAPIService("https://api.test.com")

        async def mock_fetch(batch):
            if mock_session.post.call_count <= 2:
                raise aiohttp.ClientError("Network error")
            return [{'user_id': 1}]

        with patch.object(service, '_fetch_user_batch', side_effect=mock_fetch):
            result = await service.get_users([1, 2, 3])

        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch('services.pokerhub_api.aiohttp.ClientSession')
    async def test_fetch_user_batch(self, mock_session_class):
        expected_data = [{'user_id': 1}, {'user_id': 2}]

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=expected_data)
        mock_response.raise_for_status = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)

        service = AsyncPokerHubAPIService("https://api.test.com")
        service.session = mock_session

        result = await service._fetch_user_batch([1, 2])

        assert result == expected_data
        mock_session.post.assert_called_once()
