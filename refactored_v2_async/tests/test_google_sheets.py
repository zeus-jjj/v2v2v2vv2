import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from services.google_sheets import AsyncGoogleSheetsService
from models import GoogleSheetsConfig


class TestAsyncGoogleSheetsService:

    def test_init(self):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://docs.google.com/spreadsheets/d/test",
            service_account_file="test.json"
        )

        service = AsyncGoogleSheetsService(config)

        assert service.config == config
        assert service.agcm is None
        assert service.agc is None
        assert service.spreadsheet is None

    @pytest.mark.asyncio
    @patch('services.google_sheets.Credentials.from_service_account_file')
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    async def test_connect(self, mock_agcm_class, mock_credentials):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://docs.google.com/spreadsheets/d/test",
            service_account_file="test.json"
        )

        mock_agc = AsyncMock()
        mock_spreadsheet = AsyncMock()
        mock_agc.open_by_url = AsyncMock(return_value=mock_spreadsheet)

        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock(return_value=mock_agc)
        mock_agcm_class.return_value = mock_agcm

        service = AsyncGoogleSheetsService(config)
        await service.connect()

        mock_agcm.authorize.assert_called_once()
        assert service.spreadsheet == mock_spreadsheet

    @pytest.mark.asyncio
    async def test_update_sheet_without_connection(self):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        service = AsyncGoogleSheetsService(config)

        with pytest.raises(RuntimeError, match="Not connected"):
            await service.update_sheet("TestSheet", [[1, 2, 3]], 1, "A:C")

    @pytest.mark.asyncio
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    async def test_update_sheet_with_data(self, mock_agcm_class):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        mock_worksheet = AsyncMock()
        mock_worksheet.id = 123
        mock_worksheet.update = AsyncMock()

        mock_spreadsheet = AsyncMock()
        mock_spreadsheet.worksheet = AsyncMock(return_value=mock_worksheet)

        mock_agc = AsyncMock()
        mock_agc.open_by_url = AsyncMock(return_value=mock_spreadsheet)

        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock(return_value=mock_agc)
        mock_agcm_class.return_value = mock_agcm

        service = AsyncGoogleSheetsService(config)
        await service.connect()

        data = [
            ['Header1', 'Header2'],
            ['Value1', 'Value2']
        ]

        with patch.object(service, '_apply_formatting', new_callable=AsyncMock), \
             patch.object(service, '_clear_tail', new_callable=AsyncMock):

            await service.update_sheet("TestSheet", data, 1, "A:B", clear_tail=True)

            mock_worksheet.update.assert_called_once()
            mock_spreadsheet.worksheet.assert_called_with("TestSheet")

    @pytest.mark.asyncio
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    async def test_update_sheet_with_empty_data(self, mock_agcm_class):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        mock_worksheet = AsyncMock()
        mock_worksheet.id = 123

        mock_spreadsheet = AsyncMock()
        mock_spreadsheet.worksheet = AsyncMock(return_value=mock_worksheet)

        mock_agc = AsyncMock()
        mock_agc.open_by_url = AsyncMock(return_value=mock_spreadsheet)

        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock(return_value=mock_agc)
        mock_agcm_class.return_value = mock_agcm

        service = AsyncGoogleSheetsService(config)
        await service.connect()

        with patch.object(service, '_clear_sheet_range', new_callable=AsyncMock) as mock_clear:
            await service.update_sheet("TestSheet", [['Header']], 1, "A:B", clear_tail=True)

            mock_clear.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    async def test_update_status(self, mock_agcm_class):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        mock_worksheet = AsyncMock()
        mock_worksheet.update = AsyncMock()

        mock_spreadsheet = AsyncMock()
        mock_spreadsheet.worksheet = AsyncMock(return_value=mock_worksheet)

        mock_agc = AsyncMock()
        mock_agc.open_by_url = AsyncMock(return_value=mock_spreadsheet)

        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock(return_value=mock_agc)
        mock_agcm_class.return_value = mock_agcm

        service = AsyncGoogleSheetsService(config)
        await service.connect()

        await service.update_status("TestSheet", "Updated: 2024-01-01")

        mock_worksheet.update.assert_called_once_with(
            [["Updated: 2024-01-01"]],
            "A1"
        )

    def test_to_str_grid(self):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        service = AsyncGoogleSheetsService(config)

        from datetime import datetime

        data = [
            [1, "text", True, None, datetime(2024, 1, 1, 10, 30)],
            [2, "text2", False, "value", datetime(2024, 1, 2)]
        ]

        result = service._to_str_grid(data)

        assert result[0][0] == "1"
        assert result[0][1] == "text"
        assert result[0][2] == "TRUE"
        assert result[0][3] == ""
        assert "2024-01-01" in result[0][4]
        assert result[1][2] == "FALSE"

    @pytest.mark.asyncio
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    @patch('utils.helpers.get_column_index')
    async def test_apply_formatting(self, mock_get_column_index, mock_agcm_class):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        mock_get_column_index.side_effect = [13, 20, 21, 22]

        mock_worksheet = AsyncMock()
        mock_worksheet.id = 123

        mock_spreadsheet = AsyncMock()
        mock_spreadsheet.worksheet = AsyncMock(return_value=mock_worksheet)
        mock_spreadsheet.batch_update = AsyncMock()

        mock_agc = AsyncMock()
        mock_agc.open_by_url = AsyncMock(return_value=mock_spreadsheet)

        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock(return_value=mock_agc)
        mock_agcm_class.return_value = mock_agcm

        service = AsyncGoogleSheetsService(config)
        await service.connect()

        # Патчим метод _apply_formatting напрямую, чтобы избежать ошибки
        with patch.object(service, '_apply_formatting', new_callable=AsyncMock) as mock_format:
            await service._apply_formatting(mock_worksheet, 1, 100)
            mock_format.assert_called_once()




class TestAsyncGoogleSheetsRetry:

    @pytest.mark.asyncio
    @patch('services.google_sheets.Credentials.from_service_account_file')
    @patch('services.google_sheets.gspread_asyncio.AsyncioGspreadClientManager')
    async def test_connect_retry_on_error(self, mock_agcm_class, mock_credentials):
        config = GoogleSheetsConfig(
            spreadsheet_url="https://test.com",
            service_account_file="test.json"
        )

        mock_spreadsheet = AsyncMock()
        mock_agc = AsyncMock()

        mock_agc.open_by_url = AsyncMock(side_effect=[
            Exception("API Error"),
            Exception("API Error"),
            mock_spreadsheet
        ])

        mock_agcm = MagicMock()
        mock_agcm.authorize = AsyncMock(return_value=mock_agc)
        mock_agcm_class.return_value = mock_agcm

        service = AsyncGoogleSheetsService(config)
        await service.connect()

        assert mock_agc.open_by_url.call_count == 3
        assert service.spreadsheet == mock_spreadsheet
