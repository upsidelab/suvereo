from abc import ABC

from enthusiast_common.integrations import BaseSourceIntegrationManager


class BaseECommerceIntegrationManager(BaseSourceIntegrationManager, ABC):
    """Abstract manager for integrations that provide an ECommercePlatformConnector."""
