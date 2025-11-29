
from abc import ABC, abstractmethod
from typing import List, Any


class IAsyncSheetsService(ABC):

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def update_sheet(
        self,
        tab_name: str,
        data: List[List[Any]],
        start_row: int,
        column_range: str,
        clear_tail: bool = True
    ) -> None:

        pass

    @abstractmethod
    async def update_status(self, tab_name: str, status: str) -> None:

        pass
