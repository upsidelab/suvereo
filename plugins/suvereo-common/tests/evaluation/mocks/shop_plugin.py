from abc import ABC, abstractmethod

from suvereo_common.integrations import BaseIntegration, BaseIntegrationManager

from .shop import Shop


class Catalog(ABC):
    @abstractmethod
    def list_skus(self) -> list[str]: ...


class ShopIntegrationManager(BaseIntegrationManager):
    pass


class ShopIntegrationPlugin(BaseIntegration):
    INTEGRATION_TYPE_NAME = "Shop system"
    INTEGRATION_MANAGER = ShopIntegrationManager

    @abstractmethod
    def build_shop(self) -> Shop: ...

    @abstractmethod
    def build_catalog(self) -> Catalog: ...

    @abstractmethod
    def fetch(self) -> list[dict]: ...
