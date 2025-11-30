from typing import List, Any
import gspread_asyncio
from google.oauth2.service_account import Credentials

from interfaces import IAsyncSheetsService
from models import GoogleSheetsConfig
from decorators import async_retry, log_execution, log_errors, measure_time
import logging

logger = logging.getLogger(__name__)


class AsyncGoogleSheetsService(IAsyncSheetsService):

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]

    def __init__(self, config: GoogleSheetsConfig):
        self.config = config
        self.agcm: gspread_asyncio.AsyncioGspreadClientManager = None
        self.agc: gspread_asyncio.AsyncioGspreadClient = None
        self.spreadsheet: gspread_asyncio.AsyncioGspreadSpreadsheet = None

    @log_execution()
    @async_retry(max_attempts=3)
    async def connect(self) -> None:
        def get_creds():
            return Credentials.from_service_account_file(
                self.config.service_account_file,
                scopes=self.SCOPES
            )

        self.agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
        self.agc = await self.agcm.authorize()
        self.spreadsheet = await self.agc.open_by_url(self.config.spreadsheet_url)

        logger.info("Connected to Google Sheets [ASYNC]")

    @measure_time(threshold_seconds=10.0)
    @async_retry(max_attempts=5, base_delay=1.0)
    @log_errors()
    async def update_sheet(
        self,
        tab_name: str,
        data: List[List[Any]],
        start_row: int,
        column_range: str,
        clear_tail: bool = True
    ) -> None:
        if not self.spreadsheet:
            raise RuntimeError("Not connected to Google Sheets")

        ws = await self.spreadsheet.worksheet(tab_name)

        if not data or len(data) <= 1:
            logger.warning(f"No data to write for '{tab_name}'")
            if clear_tail:
                await self._clear_sheet_range(ws, start_row, column_range)
            return

        str_data = self._to_str_grid(data)

        start_cell = f"A{start_row}"
        
        # 🚀 ОПТИМИЗАЦИЯ: Определяем тип листа по column_range
        use_pokerhub = column_range == "A:X"
        
        logger.debug(f"Writing {len(data)-1} rows to '{tab_name}' [ASYNC]")
        
        # 🚀 ОПТИМИЗАЦИЯ: Параллельное выполнение upload + formatting
        import asyncio
        await asyncio.gather(
            ws.update(str_data, start_cell, value_input_option='USER_ENTERED'),
            self._apply_formatting(ws, start_row, len(data), use_pokerhub)
        )

        logger.info(f"Wrote {len(data)-1} rows to '{tab_name}' [ASYNC]")

        # Очистка хвоста (после записи, не параллельно)
        if clear_tail:
            await self._clear_tail(ws, start_row, len(data), column_range)

    @async_retry(max_attempts=3)
    async def update_status(self, tab_name: str, status: str) -> None:
        if not self.spreadsheet:
            raise RuntimeError("Not connected to Google Sheets")

        ws = await self.spreadsheet.worksheet(tab_name)
        await ws.update([[status]], "A1")

    def _to_str_grid(self, data: List[List[Any]]) -> List[List[str]]:
        from datetime import datetime

        def format_value(v: Any) -> str:
            if v is None:
                return ''
            elif isinstance(v, bool):
                return 'TRUE' if v else 'FALSE'
            elif isinstance(v, datetime):
                return v.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return str(v)

        return [[format_value(v) for v in row] for row in data]

    async def _apply_formatting(self, ws, start_row: int, data_len: int, use_pokerhub: bool = False) -> None:
        """
        Apply formatting to sheet based on type

        Args:
            ws: Worksheet object
            start_row: Starting row number
            data_len: Number of data rows
            use_pokerhub: True for pokerhub_robot (A:X), False for standard bots (A:R)
        """
        try:
            from utils.helpers import get_column_index

            sheet_id = ws.id
            last_row = start_row + data_len - 1

            clip_format = {
                "wrapStrategy": "CLIP",
                "verticalAlignment": "TOP"
            }

            wrap_format = {
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP"
            }

            requests = []

            if use_pokerhub:
                # ========== POKERHUB_ROBOT (A:X) ==========
                logger.debug(f"Applying PokerHub formatting for '{ws.title}'")

                cols = {
                    'funnel_history': get_column_index('M'),
                    'group': get_column_index('T'),
                    'courses': get_column_index('U'),
                    'lessons': get_column_index('V')
                }

                # funnel_history, group, lessons - CLIP
                for col_name in ['funnel_history', 'group', 'lessons']:
                    col_idx = cols[col_name]
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": start_row - 1,
                                "endRowIndex": last_row,
                                "startColumnIndex": col_idx - 1,
                                "endColumnIndex": col_idx
                            },
                            "cell": {"userEnteredFormat": clip_format},
                            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
                        }
                    })

                # courses - WRAP (чтобы MTT1, MTT2 были видны построчно)
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row - 1,
                            "endRowIndex": last_row,
                            "startColumnIndex": cols['courses'] - 1,
                            "endColumnIndex": cols['courses']
                        },
                        "cell": {"userEnteredFormat": wrap_format},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
                    }
                })

                # Ширина столбцов для PokerHub
                column_widths = {
                    'funnel_history': 100,
                    'group': 120,
                    'courses': 80,
                    'lessons': 200
                }

                for col_name, width in column_widths.items():
                    col_idx = cols[col_name]
                    requests.append({
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": col_idx - 1,
                                "endIndex": col_idx
                            },
                            "properties": {"pixelSize": width},
                            "fields": "pixelSize"
                        }
                    })
            else:
                # ========== STANDARD BOTS (A:R) ==========
                logger.debug(f"Applying standard formatting for '{ws.title}'")

                funnel_col = get_column_index('M')

                # funnel_history - CLIP, узкий столбец
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row - 1,
                            "endRowIndex": last_row,
                            "startColumnIndex": funnel_col - 1,
                            "endColumnIndex": funnel_col
                        },
                        "cell": {"userEnteredFormat": clip_format},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"
                    }
                })

                # Ширина столбца funnel_history
                requests.append({
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": funnel_col - 1,
                            "endIndex": funnel_col
                        },
                        "properties": {"pixelSize": 100},
                        "fields": "pixelSize"
                    }
                })

            # ========== ОБЩЕЕ ДЛЯ ВСЕХ ТИПОВ ЛИСТОВ ==========
            # Фиксированная высота строк
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start_row - 1,
                        "endIndex": last_row
                    },
                    "properties": {"pixelSize": 100},
                    "fields": "pixelSize"
                }
            })

            # Выполняем все запросы форматирования
            if requests:
                await self.spreadsheet.batch_update(body={"requests": requests})
                logger.debug(f"Formatting applied for '{ws.title}' [ASYNC]")

        except Exception as e:
            logger.warning(f"Failed to apply formatting for '{ws.title}': {e}")

    async def _clear_tail(self, ws, start_row: int, data_len: int, column_range: str) -> None:
        from utils.helpers import get_column_range_end

        end_row_current = ws.row_count
        tail_start = start_row + data_len

        if end_row_current >= tail_start:
            end_col_letter = get_column_range_end(column_range)
            await ws.batch_clear([
                f"{column_range.split(':')[0]}{tail_start}:{end_col_letter}{end_row_current}"
            ])

    async def _clear_sheet_range(self, ws, start_row: int, column_range: str) -> None:
        from utils.helpers import get_column_range_end

        end_row_current = ws.row_count
        end_col_letter = get_column_range_end(column_range)
        await ws.batch_clear([
            f"{column_range.split(':')[0]}{start_row}:{end_col_letter}{end_row_current}"
        ])
