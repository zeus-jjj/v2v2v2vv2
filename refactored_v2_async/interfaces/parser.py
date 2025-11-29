
from abc import ABC, abstractmethod
from typing import Any, Tuple


class IParser(ABC):

    @abstractmethod
    def parse(self, data: Any) -> Tuple[str, str]:

        pass
