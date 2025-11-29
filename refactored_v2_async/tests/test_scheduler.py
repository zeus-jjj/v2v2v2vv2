import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.scheduler import AsyncScheduler
from models import Settings


class TestAsyncScheduler:

    def test_init(self, mock_settings):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_parser = MagicMock()
        mock_factory = MagicMock()
        mock_db_service_factory = MagicMock()

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        assert scheduler.settings == mock_settings
        assert scheduler.sheets_service == mock_sheets
        assert scheduler.api_service == mock_api
        assert scheduler.parser == mock_parser
        assert scheduler.db_factory == mock_factory
        assert scheduler.db_service_factory == mock_db_service_factory
        assert scheduler.db_configs == []

    @pytest.mark.asyncio
    @patch('services.scheduler.asyncio.sleep')
    async def test_update_all_sheets(self, mock_sleep, mock_settings, mock_db_config):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_parser = MagicMock()
        mock_factory = MagicMock()
        mock_db_service_factory = MagicMock()

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        scheduler.db_configs = [mock_db_config, mock_db_config]

        with patch.object(scheduler, '_update_single_sheet', new_callable=AsyncMock) as mock_update:
            await scheduler.update_all_sheets()

            assert mock_update.call_count == 2

    @pytest.mark.asyncio
    async def test_update_single_sheet_standard(self, mock_settings, mock_db_config, mock_db_rows):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_parser = MagicMock()
        mock_factory = MagicMock()

        mock_db_instance = AsyncMock()
        mock_db_instance.fetch_data = AsyncMock(return_value=mock_db_rows)
        mock_db_instance.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db_instance.__aexit__ = AsyncMock()

        mock_db_service_factory = MagicMock(return_value=mock_db_instance)

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        await scheduler._update_single_sheet(mock_db_config)

        mock_db_instance.fetch_data.assert_called_once()
        mock_sheets.update_sheet.assert_called_once()
        mock_sheets.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_single_sheet_with_pokerhub(self, mock_settings, mock_db_config_with_pokerhub,
                                                      mock_db_rows, mock_pokerhub_response):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_api.get_users = AsyncMock(return_value=mock_pokerhub_response)

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ("MTT1\nSPIN1", "Lesson 1\nLesson 2")

        mock_factory = MagicMock()

        mock_db_rows_with_datetime = [
            mock_db_rows[0],
            [1, 'user1', 'John', 'Doe', datetime.now(), datetime.now(), 'active']
        ]

        mock_db_instance = AsyncMock()
        mock_db_instance.fetch_data = AsyncMock(return_value=mock_db_rows_with_datetime)
        mock_db_instance.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db_instance.__aexit__ = AsyncMock()

        mock_db_service_factory = MagicMock(return_value=mock_db_instance)

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        await scheduler._update_single_sheet(mock_db_config_with_pokerhub)

        mock_api.get_users.assert_called_once()
        mock_parser.parse.assert_called()
        mock_sheets.update_sheet.assert_called_once()

    @pytest.mark.asyncio
    async def test_integrate_pokerhub_data(self, mock_settings, mock_db_config_with_pokerhub,
                                           mock_db_rows, mock_pokerhub_response):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_api.get_users = AsyncMock(return_value=mock_pokerhub_response)

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ("MTT1", "Lesson 1")

        mock_factory = MagicMock()
        mock_db_service_factory = MagicMock()

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        user_data_with_datetime = [
            [1, 'user1', 'John', 'Doe', datetime.now(), datetime.now(), 'active']
        ]
        headers = mock_db_rows[0]

        merged_data, merged_headers = await scheduler._integrate_pokerhub_data(
            user_data_with_datetime,
            headers,
            mock_db_config_with_pokerhub
        )

        assert len(merged_headers) > len(headers)
        assert 'ph_utm_medium' in merged_headers
        assert 'courses' in merged_headers
        assert 'lessons' in merged_headers

    @pytest.mark.asyncio
    async def test_integrate_pokerhub_data_no_users(self, mock_settings, mock_db_config_with_pokerhub):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_parser = MagicMock()
        mock_factory = MagicMock()
        mock_db_service_factory = MagicMock()

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        user_data = []
        headers = ['id', 'username']

        result_data, result_headers = await scheduler._integrate_pokerhub_data(
            user_data,
            headers,
            mock_db_config_with_pokerhub
        )

        assert result_data == user_data
        assert result_headers == headers

    def test_build_merged_row(self, mock_settings, mock_db_config_with_pokerhub):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ("MTT1\nSPIN1", "Lesson 1\nLesson 2")

        mock_factory = MagicMock()
        mock_db_service_factory = MagicMock()

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        row = [1, 'user1', 'John', 'Doe', datetime.now(), datetime.now(), 'active']

        ph_user_data = {
            'utm': {'utm_medium': 'social', 'utm_source': 'facebook'},
            'referer': 'https://ref.com',
            'authorization_date': '2024-01-01T10:00:00Z',
            'last_visit_date': '2024-01-15T15:00:00Z',
            'group': ['Group1', 'MTT Course'],
            'courses': {'MTT Course 1': ['Lesson 1']},
            'lessons': ['Lesson 2']
        }

        merged_row = scheduler._build_merged_row(
            row,
            ph_user_data,
            ph_user_data.get('utm', {}),
            mock_db_config_with_pokerhub
        )

        assert len(merged_row) > len(row)
        assert 'social' in merged_row
        assert 'facebook' in merged_row


class TestAsyncSchedulerEdgeCases:

    @pytest.mark.asyncio
    async def test_update_single_sheet_with_empty_data(self, mock_settings, mock_db_config):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_parser = MagicMock()
        mock_factory = MagicMock()

        mock_db_instance = AsyncMock()
        mock_db_instance.fetch_data = AsyncMock(return_value=[['id', 'username']])
        mock_db_instance.__aenter__ = AsyncMock(return_value=mock_db_instance)
        mock_db_instance.__aexit__ = AsyncMock()

        mock_db_service_factory = MagicMock(return_value=mock_db_instance)

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=mock_db_service_factory
        )

        await scheduler._update_single_sheet(mock_db_config)

        mock_sheets.update_sheet.assert_called_once()

        status_call = mock_sheets.update_status.call_args[0][1]
        assert "0" in status_call

    @pytest.mark.asyncio
    async def test_update_all_sheets_with_errors(self, mock_settings, mock_db_config):
        mock_sheets = AsyncMock()
        mock_api = AsyncMock()
        mock_parser = MagicMock()
        mock_factory = MagicMock()

        scheduler = AsyncScheduler(
            settings=mock_settings,
            sheets_service=mock_sheets,
            api_service=mock_api,
            parser=mock_parser,
            db_factory=mock_factory,
            db_service_factory=MagicMock()
        )

        scheduler.db_configs = [mock_db_config, mock_db_config]

        mock_db_instance_success = AsyncMock()
        mock_db_instance_success.fetch_data = AsyncMock(return_value=[])
        mock_db_instance_success.__aenter__ = AsyncMock(return_value=mock_db_instance_success)
        mock_db_instance_success.__aexit__ = AsyncMock()

        mock_db_instance_fail = AsyncMock()
        mock_db_instance_fail.fetch_data = AsyncMock(side_effect=Exception("DB Error"))
        mock_db_instance_fail.__aenter__ = AsyncMock(side_effect=Exception("DB Error"))
        mock_db_instance_fail.__aexit__ = AsyncMock()

        call_count = [0]

        def factory_side_effect(config):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_db_instance_success
            else:
                return mock_db_instance_fail

        scheduler.db_service_factory = MagicMock(side_effect=factory_side_effect)

        await scheduler.update_all_sheets()

        mock_sheets.update_sheet.assert_called_once()
