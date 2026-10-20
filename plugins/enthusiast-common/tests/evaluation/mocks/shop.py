from abc import ABC, abstractmethod

from enthusiast_common.evaluation.mocks import BaseMock


class ShopError(Exception):
    pass


class Shop(ABC):
    @abstractmethod
    def create_order(self, items: list, email: str | None = None) -> str: ...

    @abstractmethod
    def get_product(self, sku: str) -> dict | None: ...

    @abstractmethod
    async def ping(self) -> bool: ...

    @abstractmethod
    def search(self, query: str, n: int = 10, **filters) -> list: ...

    def describe(self) -> str:
        return "real"

    @staticmethod
    def currencies() -> list[str]:
        return ["EUR"]


class ShopMock(BaseMock):
    INTERFACE = Shop
    ERRORS = {"ShopError": ShopError}
