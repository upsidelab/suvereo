from abc import ABC

from enthusiast_common.integrations import BaseSourceIntegrationManager


class BaseDocumentSourceManager(BaseSourceIntegrationManager, ABC):
    """Abstract manager for integrations that fetch documents from an external source."""
