
import re
from typing import List, Any, Tuple, Optional

from interfaces import IParser
from decorators import log_execution, cache_result
import logging

logger = logging.getLogger(__name__)


class CourseParser(IParser):

    COURSE_PATTERNS = {
        'MTT': 'MTT',
        'МТТ': 'MTT',
        'SPIN': 'SPIN',
        'СПИН': 'SPIN',
        'CASH': 'CASH',
        'КЭШ': 'CASH',
        'КЕШ': 'CASH',
    }

    TEXT_NUMBERS = {
        'ПЕРВЫЙ': '1', 'FIRST': '1', 'BEGINNER': '1', 'НАЧИНАЮЩ': '1', 'ОСНОВ': '1',
        'ВТОРОЙ': '2', 'SECOND': '2', 'MIDDLE': '2', 'СРЕДН': '2',
        'ТРЕТИЙ': '3', 'THIRD': '3', 'ADVANCED': '3', 'ПРОДВИНУТ': '3',
        'ЧЕТВЕРТЫЙ': '4', 'FOURTH': '4', 'PRO': '4', 'ПРОФЕСС': '4',
    }

    @log_execution()
    def parse(self, data: List[Any]) -> Tuple[str, str]:

        courses_set = set()
        lessons_list = []

        if not isinstance(data, list):
            data = [data] if data else []

        for item in data:
            if item is None:
                continue

            if isinstance(item, dict):
                self._process_dict_item(item, courses_set, lessons_list)
            elif isinstance(item, str):
                self._process_string_item(item, courses_set, lessons_list)

        courses_str = "\n".join(sorted(courses_set))
        lessons_str = "\n".join(self._sort_lessons(lessons_list))

        if len(lessons_str) > 45000:
            lessons_str = self._truncate_lessons(lessons_list)

        return courses_str, lessons_str

    def _process_dict_item(
        self,
        item: dict,
        courses_set: set,
        lessons_list: list
    ) -> None:
        for course_name, course_lessons in item.items():
            course_type = self.identify_course_type(course_name)
            if course_type:
                courses_set.add(course_type)

            if isinstance(course_lessons, list):
                for lesson in course_lessons:
                    if lesson:
                        lessons_list.append(str(lesson))

                        lesson_type = self.identify_course_type(str(lesson))
                        if lesson_type:
                            courses_set.add(lesson_type)

    def _process_string_item(
        self,
        item: str,
        courses_set: set,
        lessons_list: list
    ) -> None:
        course_type = self.identify_course_type(item)
        if course_type:
            courses_set.add(course_type)

        if any(marker in item for marker in ['Модуль', 'Урок', 'модуль', 'урок']):
            lessons_list.append(item)

    @cache_result(maxsize=256)
    def identify_course_type(self, text: str) -> Optional[str]:

        if not text:
            return None

        text_upper = text.upper()

        for pattern, course_type in self.COURSE_PATTERNS.items():
            if pattern not in text_upper:
                continue

            module_match = re.search(r'МОДУЛЬ\s*(\d+)', text_upper)
            if module_match:
                return f"{course_type}{module_match.group(1)}"

            numbers = re.findall(r'(\d+)', text)
            if numbers:
                return f"{course_type}{numbers[0]}"

            for text_num, digit in self.TEXT_NUMBERS.items():
                if text_num in text_upper:
                    return f"{course_type}{digit}"

            return f"{course_type}1"

        return None

    def _sort_lessons(self, lessons: List[str]) -> List[str]:
        def extract_sort_key(lesson: str) -> Tuple[str, int, int]:
            lesson_upper = lesson.upper()

            if 'MTT' in lesson_upper or 'МТТ' in lesson_upper:
                course_type = 'MTT'
            elif 'SPIN' in lesson_upper or 'СПИН' in lesson_upper:
                course_type = 'SPIN'
            elif 'CASH' in lesson_upper or 'КЭШ' in lesson_upper or 'КЕШ' in lesson_upper:
                course_type = 'CASH'
            else:
                course_type = 'ZZZ'

            module_match = re.search(r'[Мм]одуль\s*(\d+)', lesson)
            module_num = int(module_match.group(1)) if module_match else 999

            lesson_match = re.search(r'[Уу]рок\s*(\d+)', lesson)
            lesson_num = int(lesson_match.group(1)) if lesson_match else 999

            return (course_type, module_num, lesson_num)

        try:
            return sorted(lessons, key=extract_sort_key)
        except Exception as e:
            logger.warning(f"Failed to sort lessons: {e}")
            return lessons

    def _truncate_lessons(self, lessons: List[str]) -> str:
        if len(lessons) > 60:
            truncated = (
                lessons[:30] +
                [f"... [{len(lessons)-60} lessons skipped] ..."] +
                lessons[-30:]
            )
            return "\n".join(truncated)
        else:
            lessons_str = "\n".join(lessons)
            return lessons_str[:45000] + "\n[TRUNCATED]"
