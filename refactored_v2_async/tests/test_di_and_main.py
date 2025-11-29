"""
Tests for async DI container and main module
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from injector import Injector

from di_container import AsyncApplicationModule
from models import Settings
from interfaces import IAsyncSheetsService, IAsyncAPIService, IParser
from services import AsyncGoogleSheetsService, AsyncPokerHubAPIService, AsyncScheduler
from parsers import CourseParser
from config import DatabaseConfigFactory


class TestAsyncApplicationModule:

    def test_module_initialization(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)

        assert module.settings == mock_settings

    def test_configure_binds_settings(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)
        injector = Injector([module])

        settings = injector.get(Settings)

        assert settings == mock_settings

    def test_provide_sheets_service(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)

        with patch('di_container.AsyncGoogleSheetsService') as mock_service_class:
            service = module.provide_sheets_service(mock_settings)

            mock_service_class.assert_called_once_with(
                mock_settings.google_sheets_config
            )

    def test_provide_api_service(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)

        with patch('di_container.AsyncPokerHubAPIService') as mock_service_class:
            service = module.provide_api_service(mock_settings)

            mock_service_class.assert_called_once_with(
                mock_settings.pokerhub_api_url
            )

    def test_provide_parser(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)

        with patch('di_container.CourseParser') as mock_parser_class:
            parser = module.provide_parser()

            mock_parser_class.assert_called_once()

    def test_provide_database_factory(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)

        with patch('di_container.DatabaseConfigFactory') as mock_factory_class:
            factory = module.provide_database_factory(mock_settings)

            mock_factory_class.assert_called_once_with(mock_settings)

    def test_injector_resolves_all_dependencies(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)
        injector = Injector([module])

        sheets = injector.get(IAsyncSheetsService)
        api = injector.get(IAsyncAPIService)
        parser = injector.get(IParser)
        factory = injector.get(DatabaseConfigFactory)

        assert sheets is not None
        assert api is not None
        assert parser is not None
        assert factory is not None

    def test_injector_resolves_scheduler(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)
        injector = Injector([module])

        scheduler = injector.get(AsyncScheduler)

        assert isinstance(scheduler, AsyncScheduler)
        assert scheduler.settings == mock_settings

    def test_singleton_scope(self, mock_settings):
        module = AsyncApplicationModule(mock_settings)
        injector = Injector([module])

        sheets1 = injector.get(IAsyncSheetsService)
        sheets2 = injector.get(IAsyncSheetsService)

        assert sheets1 is sheets2


class TestMain:

    @patch('main.Injector')
    @patch('main.Settings')
    @patch('main.logging.basicConfig')
    def test_setup_logging(self, mock_logging, mock_settings_class, mock_injector_class):
        from main import setup_logging

        setup_logging("DEBUG")

        mock_logging.assert_called_once()
        call_kwargs = mock_logging.call_args[1]
        assert 'level' in call_kwargs
        assert 'format' in call_kwargs

    @pytest.mark.asyncio
    @patch('main.AsyncScheduler')
    @patch('main.Injector')
    @patch('main.Settings')
    async def test_async_main_success(self, mock_settings_class, mock_injector_class,
                                      mock_scheduler_class):
        from main import async_main

        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_settings_class.return_value = mock_settings

        mock_injector = MagicMock()
        mock_scheduler = AsyncMock()
        mock_scheduler.run = AsyncMock(side_effect=KeyboardInterrupt())
        mock_injector.get.return_value = mock_scheduler
        mock_injector_class.return_value = mock_injector

        with patch('main.setup_logging'):
            try:
                await async_main()
            except KeyboardInterrupt:
                pass

        mock_settings_class.assert_called_once()

        mock_injector_class.assert_called_once()

        mock_injector.get.assert_called_once()

        mock_scheduler.run.assert_called_once()

    @pytest.mark.asyncio
    @patch('main.AsyncScheduler')
    @patch('main.Injector')
    @patch('main.Settings')
    async def test_async_main_keyboard_interrupt(self, mock_settings_class,
                                                 mock_injector_class, mock_scheduler_class):
        from main import async_main

        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_settings_class.return_value = mock_settings

        mock_injector = MagicMock()
        mock_scheduler = AsyncMock()
        mock_scheduler.run = AsyncMock(side_effect=KeyboardInterrupt())
        mock_injector.get.return_value = mock_scheduler
        mock_injector_class.return_value = mock_injector

        with patch('main.setup_logging'):
            await async_main()

    @pytest.mark.asyncio
    @patch('main.AsyncScheduler')
    @patch('main.Injector')
    @patch('main.Settings')
    async def test_async_main_exception(self, mock_settings_class,
                                       mock_injector_class, mock_scheduler_class):
        from main import async_main

        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_settings_class.return_value = mock_settings

        mock_injector_class.side_effect = Exception("Test error")

        with patch('main.setup_logging'), \
             patch('main.sys.exit') as mock_exit:
            await async_main()

            mock_exit.assert_called_once_with(1)


class TestFullAsyncIntegration:

    @pytest.mark.asyncio
    @patch('services.google_sheets.Credentials')
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    async def test_full_di_chain(self, mock_agcm_class, mock_credentials, mock_settings):
        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock()
        mock_agcm_class.return_value = mock_agcm

        module = AsyncApplicationModule(mock_settings)
        injector = Injector([module])

        scheduler = injector.get(AsyncScheduler)

        assert scheduler.settings is not None
        assert scheduler.sheets_service is not None
        assert scheduler.api_service is not None
        assert scheduler.parser is not None
        assert scheduler.db_factory is not None

    def test_di_without_optional_ssh(self):
        settings = Settings(
            spreadsheet_url="https://test.com",
            db_password="test",
            ssh_host=None,
            ssh_user=None,
            ssh_password=None
        )

        module = AsyncApplicationModule(settings)
        injector = Injector([module])

        factory = injector.get(DatabaseConfigFactory)
        assert factory is not None

        ssh_config = settings.get_ssh_config()
        assert ssh_config is None
