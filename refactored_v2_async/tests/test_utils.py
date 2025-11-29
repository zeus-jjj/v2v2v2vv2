
import pytest
from datetime import datetime

from utils import (
    now_time,
    make_status_line,
    get_column_letter,
    get_column_range_end,
    get_column_index,
    parse_to_gs_date
)


class TestTimeUtils:

    def test_now_time_default_timezone(self):
        result = now_time()

        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_now_time_custom_timezone(self):
        result = now_time("America/New_York")

        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_now_time_invalid_timezone(self):
        result = now_time("Invalid/Timezone")

        assert isinstance(result, datetime)

    def test_make_status_line(self):
        result = make_status_line("TestSheet", 100)

        assert "TestSheet" in result
        assert "100" in result
        assert "records:" in result
        assert "-" in result
        assert ":" in result


class TestColumnUtils:

    def test_get_column_letter_single(self):
        assert get_column_letter(1) == "A"
        assert get_column_letter(2) == "B"
        assert get_column_letter(26) == "Z"

    def test_get_column_letter_double(self):
        assert get_column_letter(27) == "AA"
        assert get_column_letter(28) == "AB"
        assert get_column_letter(52) == "AZ"

    def test_get_column_letter_triple(self):
        assert get_column_letter(703) == "AAA"

    def test_get_column_index_single(self):
        assert get_column_index("A") == 1
        assert get_column_index("B") == 2
        assert get_column_index("Z") == 26

    def test_get_column_index_double(self):
        assert get_column_index("AA") == 27
        assert get_column_index("AB") == 28
        assert get_column_index("AZ") == 52

    def test_get_column_index_lowercase(self):
        assert get_column_index("a") == 1
        assert get_column_index("aa") == 27

    def test_get_column_range_end(self):
        assert get_column_range_end("A:Z") == "Z"
        assert get_column_range_end("B:AZ") == "AZ"
        assert get_column_range_end("A:AAA") == "AAA"

    def test_get_column_range_end_no_colon(self):
        assert get_column_range_end("Z") == "Z"

    def test_column_letter_index_roundtrip(self):
        for i in range(1, 100):
            letter = get_column_letter(i)
            index = get_column_index(letter)
            assert index == i

    def test_cache_result_on_column_functions(self):
        for _ in range(10):
            get_column_letter(1)
            get_column_index("A")

        cache_info_letter = get_column_letter.cache_info()
        cache_info_index = get_column_index.cache_info()

        assert cache_info_letter.hits > 0
        assert cache_info_index.hits > 0


class TestDateParsing:

    def test_parse_to_gs_date_iso_format(self):
        result = parse_to_gs_date("2024-01-15T10:30:00Z")

        assert "2024-01-15" in result
        assert "10:30:00" in result

    def test_parse_to_gs_date_iso_with_offset(self):
        result = parse_to_gs_date("2024-01-15T10:30:00+03:00")

        assert "2024-01-15" in result

    def test_parse_to_gs_date_empty_string(self):
        result = parse_to_gs_date("")

        assert result == ""

    def test_parse_to_gs_date_none(self):
        result = parse_to_gs_date(None)

        assert result == ""

    def test_parse_to_gs_date_invalid_format(self):
        result = parse_to_gs_date("invalid date")

        assert result == "invalid date"

    def test_parse_to_gs_date_already_formatted(self):
        input_date = "2024-01-15 10:30:00"
        result = parse_to_gs_date(input_date)

        assert isinstance(result, str)
