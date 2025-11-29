
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IAsyncAPIService(ABC):

    @abstractmethod
    async def get_users(self, user_ids: List[int]) -> List[Dict[str, Any]]:

        pass

    @abstractmethod
    async def health_check(self) -> bool:

        pass
