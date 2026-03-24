from abc import ABC, abstractmethod
from typing import Awaitable, Optional, TypeVar


_T = TypeVar("_T")


class BaseScraper(ABC):

    def __init__(self, url: str, keyword: str):
        self.url = url
        self.keyword = keyword

    @abstractmethod
    async def check_status(self) -> bool:
        pass
