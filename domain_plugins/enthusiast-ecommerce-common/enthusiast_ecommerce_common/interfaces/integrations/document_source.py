from abc import abstractmethod

from enthusiast_common.integrations import BaseIntegration

from enthusiast_ecommerce_common.interfaces.integration_managers import BaseDocumentSourceManager
from enthusiast_ecommerce_common.structures import DocumentDetails


class DocumentSourcePlugin(BaseIntegration):
    """Fetches documents from an external source.

    Subclasses must declare ``TYPE``, ``NAME``, and implement ``fetch()``.
    Persistence is handled by the vertical's ``DocumentSourceManager``.
    """

    INTEGRATION_MANAGER = BaseDocumentSourceManager

    @abstractmethod
    def fetch(self) -> list[DocumentDetails]:
        """Return all documents available from this source."""
