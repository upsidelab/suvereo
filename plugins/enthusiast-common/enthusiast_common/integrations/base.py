from abc import ABC, abstractmethod
from typing import Any


class BaseIntegrationType(ABC):
    """Marker base for a category of integrations."""


class BaseSourceIntegrationType(BaseIntegrationType):
    """Marker for integration categories whose plugins pull data from an external source."""

    @abstractmethod
    def sync(self, plugin: Any, dataset_id: Any) -> None:
        """Pull data from the plugin's external source into the DataSet."""


class BaseIntegration(ABC):
    """A connection to one external system, declared by a vertical.

    The framework stores the integration's configuration and instantiates the
    plugin with that config before use. A DataSet holds at most one integration
    of a given ``TYPE``. A vertical may add further capabilities in its own
    subclass; the base only covers config and connection testing.
    """

    #: Stable identifier for this integration type. Unique per DataSet.
    TYPE: str
    #: Human-readable name shown in the UI.
    LABEL: str
    #: Category this integration belongs to. Verticals set this on their plugin ABCs.
    INTEGRATION_TYPE: type[BaseIntegrationType] | None = None

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def get_config_schema(self) -> Any:
        """Describe the config fields this integration accepts, to drive its config form."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Check that ``self.config`` can reach the external system."""
