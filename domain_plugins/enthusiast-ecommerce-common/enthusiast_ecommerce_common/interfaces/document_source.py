from abc import abstractmethod
from typing import Any

from enthusiast_common.integrations import BaseIntegration

from enthusiast_ecommerce_common.structures import DocumentDetails
from enthusiast_ecommerce_common.types import DocumentSourceType


class DocumentSourcePlugin(BaseIntegration):
    """Fetches documents from an external source.

    Subclasses must declare ``TYPE``, ``LABEL``, and implement ``fetch()``.
    Persistence is handled by the vertical's ``DocumentSyncManager``.
    """

    INTEGRATION_TYPE = DocumentSourceType

    def get_config_schema(self) -> Any:
        return {}

    def test_connection(self) -> bool:
        return True

    @abstractmethod
    def fetch(self) -> list[DocumentDetails]:
        """Return all documents available from this source."""
