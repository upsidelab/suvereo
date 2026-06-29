from abc import abstractmethod

from enthusiast_common.integrations import BaseIntegration

from enthusiast_ecommerce_common.connectors import ECommercePlatformConnector
from enthusiast_ecommerce_common.types import ECommerceIntegrationType


class ECommerceIntegrationPlugin(BaseIntegration):
    """A BaseIntegration that also exposes an ECommercePlatformConnector for agent tools."""

    INTEGRATION_TYPE = ECommerceIntegrationType

    @abstractmethod
    def build_connector(self) -> ECommercePlatformConnector:
        """Return a connector for the e-commerce platform this integration manages."""
        pass
