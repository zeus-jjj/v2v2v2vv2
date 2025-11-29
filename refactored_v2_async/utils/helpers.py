
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from decorators import cache_result
import logging

logger = logging.getLogger(__name__)


def now_time(timezone: str = "Europe/Moscow") -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        logger.warning(f"ZoneInfo '{timezone}' not available. Using local time.")
        return datetime.now()


def make_status_line(tab_name: str, rows_count: int) -> str:
    dt = now_time().strftime("%Y-%m-%d %H:%M:%S")
    return f"{dt} | {tab_name} | records: {rows_count}"


@cache_result(maxsize=256)
def get_column_letter(n: int) -> str:
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def get_column_range_end(range_str: str) -> str:
    return range_str.split(':')[1] if ':' in range_str else range_str


@cache_result(maxsize=256)
def get_column_index(col_letter: str) -> int:
    index = 0
    for char in col_letter.upper():
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index


def parse_to_gs_date(date_str: str) -> str:
    if not date_str:
        return ''

    try:
        from datetime import datetime as dt_parser
        parsed_dt = dt_parser.fromisoformat(date_str.replace('Z', '+00:00'))
        return parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return date_str
