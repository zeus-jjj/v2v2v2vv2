
from abc import ABC, abstractmethod
from typing import List, Any


class IAsyncDatabaseService(ABC):

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def fetch_data(self) -> List[List[Any]]:

        pass

    @abstractmethod
    async def execute_query(self, query: str, params: tuple = None) -> List[tuple]:

        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
