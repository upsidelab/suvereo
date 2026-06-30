from abc import abstractmethod

from enthusiast_common.integrations import BaseIntegration

from enthusiast_ecommerce_common.structures import ProductDetails
from enthusiast_ecommerce_common.types import ProductSourceType


class ProductSourcePlugin(BaseIntegration):
    """Fetches products from an external source.

    Subclasses must declare ``TYPE``, ``LABEL``, and implement ``fetch()``.
    Persistence is handled by the vertical's ``ProductSyncManager``.
    """

    INTEGRATION_TYPE = ProductSourceType

    def test_connection(self) -> bool:
        return True

    @abstractmethod
    def fetch(self) -> list[ProductDetails]:
        """Return all products available from this source."""
