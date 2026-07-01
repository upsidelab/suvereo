from abc import abstractmethod

from enthusiast_common.integrations import BaseIntegration

from enthusiast_ecommerce_common.interfaces.integration_managers import BaseProductSourceManager
from enthusiast_ecommerce_common.structures import ProductDetails


class ProductSourcePlugin(BaseIntegration):
    """Fetches products from an external source.

    Subclasses must declare ``TYPE``, ``NAME``, and implement ``fetch()``.
    Persistence is handled by the vertical's ``ProductSourceManager``.
    """

    INTEGRATION_MANAGER = BaseProductSourceManager

    @abstractmethod
    def fetch(self) -> list[ProductDetails]:
        """Return all products available from this source."""
