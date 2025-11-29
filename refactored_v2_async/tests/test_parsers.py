
import pytest
from parsers import CourseParser


class TestCourseParser:

    def test_init(self):
        parser = CourseParser()
        assert parser is not None

    def test_parse_empty_data(self):
        parser = CourseParser()
        courses, lessons = parser.parse([])

        assert courses == ""
        assert lessons == ""

    def test_parse_dict_item(self):
        parser = CourseParser()

        data = [
            {"MTT Course 1": ["Модуль 1 Урок 1", "Модуль 1 Урок 2"]}
        ]

        courses, lessons = parser.parse(data)

        assert "MTT" in courses
        assert "Модуль 1 Урок 1" in lessons

    def test_parse_string_item(self):
        parser = CourseParser()

        data = ["MTT Course Модуль 1", "SPIN Course"]

        courses, lessons = parser.parse(data)

        assert "MTT" in courses or "SPIN" in courses

    def test_parse_mixed_data(self):
        parser = CourseParser()

        data = [
            {"MTT Course 1": ["Модуль 1 Урок 1"]},
            "SPIN Course 2",
            {"CASH Course": ["Модуль 2 Урок 3"]}
        ]

        courses, lessons = parser.parse(data)

        assert courses
        assert lessons

    def test_parse_with_none_values(self):
        parser = CourseParser()

        data = [None, {"MTT": ["Lesson"]}, None]

        courses, lessons = parser.parse(data)

        assert "MTT" in courses

    def test_identify_course_type_mtt(self):
        parser = CourseParser()

        assert parser.identify_course_type("MTT Course 1") == "MTT1"
        assert parser.identify_course_type("МТТ Курс 1") == "MTT1"
        assert parser.identify_course_type("MTT Модуль 2") == "MTT2"

    def test_identify_course_type_spin(self):
        parser = CourseParser()

        assert parser.identify_course_type("SPIN Course 1") == "SPIN1"
        assert parser.identify_course_type("СПИН Курс 2") == "SPIN2"

    def test_identify_course_type_cash(self):
        parser = CourseParser()

        assert parser.identify_course_type("CASH Course 1") == "CASH1"
        assert parser.identify_course_type("КЭШ Курс 2") == "CASH2"
        assert parser.identify_course_type("КЕШ Модуль 3") == "CASH3"

    def test_identify_course_type_with_text_numbers(self):
        parser = CourseParser()

        assert parser.identify_course_type("MTT ПЕРВЫЙ") == "MTT1"
        assert parser.identify_course_type("SPIN ВТОРОЙ") == "SPIN2"
        assert parser.identify_course_type("CASH ТРЕТИЙ") == "CASH3"
        assert parser.identify_course_type("MTT BEGINNER") == "MTT1"
        assert parser.identify_course_type("SPIN ADVANCED") == "SPIN3"

    def test_identify_course_type_default_to_1(self):
        parser = CourseParser()

        assert parser.identify_course_type("MTT Course") == "MTT1"
        assert parser.identify_course_type("SPIN") == "SPIN1"

    def test_identify_course_type_returns_none(self):
        parser = CourseParser()

        assert parser.identify_course_type("Unknown Course") is None
        assert parser.identify_course_type("") is None
        assert parser.identify_course_type(None) is None

    def test_sort_lessons(self):
        parser = CourseParser()

        lessons = [
            "MTT Модуль 2 Урок 1",
            "MTT Модуль 1 Урок 2",
            "SPIN Модуль 1 Урок 1",
            "MTT Модуль 1 Урок 1",
            "CASH Модуль 1 Урок 1"
        ]

        sorted_lessons = parser._sort_lessons(lessons)

        assert "CASH" in sorted_lessons[0]
        assert "MTT" in sorted_lessons[1]
        assert "Модуль 1" in sorted_lessons[1]

    def test_sort_lessons_with_invalid_data(self):
        parser = CourseParser()

        lessons = ["Invalid lesson without proper format"]

        sorted_lessons = parser._sort_lessons(lessons)
        assert len(sorted_lessons) == 1

    def test_truncate_lessons(self):
        parser = CourseParser()

        lessons = [f"MTT Модуль {i} Урок 1" for i in range(1, 101)]

        truncated = parser._truncate_lessons(lessons)

        assert "[" in truncated and "skipped" in truncated.lower() or "TRUNCATED" in truncated

    def test_truncate_lessons_short_list(self):
        parser = CourseParser()

        lessons = [f"Lesson {i}" for i in range(1, 50)]

        truncated = parser._truncate_lessons(lessons)

        assert len(truncated) < 45001

    def test_parse_handles_very_long_lessons_list(self):
        parser = CourseParser()

        data = [
            {f"MTT Course {i}": [f"Модуль {j} Урок {k}"
                                 for j in range(1, 11)
                                 for k in range(1, 11)]
             for i in range(1, 11)}
        ]

        courses, lessons = parser.parse(data)

        assert len(lessons) < 50000

    def test_cache_result_decorator(self):
        parser = CourseParser()

        result1 = parser.identify_course_type("MTT Course 1")
        result2 = parser.identify_course_type("MTT Course 1")
        result3 = parser.identify_course_type("MTT Course 1")

        assert result1 == result2 == result3 == "MTT1"

        cache_info = parser.identify_course_type.cache_info()
        assert cache_info.hits >= 2
