from abc import abstractmethod
from typing import TYPE_CHECKING

from enthusiast_common.integrations import BaseIntegration

from enthusiast_ecommerce_common.connectors import ECommercePlatformConnector
from enthusiast_ecommerce_common.types import ECommerceIntegrationType

if TYPE_CHECKING:
    from enthusiast_ecommerce_common.interfaces.product_source import ProductSourcePlugin


class ECommerceIntegrationPlugin(BaseIntegration):
    """A BaseIntegration that provides a platform connector and a product data source."""

    INTEGRATION_TYPE = ECommerceIntegrationType

    @abstractmethod
    def build_connector(self) -> ECommercePlatformConnector:
        """Return a connector for the e-commerce platform this integration manages."""

    @abstractmethod
    def build_product_source(self) -> "ProductSourcePlugin":
        """Return a ProductSourcePlugin configured with this integration's credentials."""
