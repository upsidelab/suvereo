from abc import ABC, abstractmethod
from typing import Any


class BaseIntegrationManager(ABC):
    """Marker base for a category of integrations."""


class BaseSourceIntegrationManager(BaseIntegrationManager):
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
    INTEGRATION_MANAGER: type[BaseIntegrationManager] | None = None
    #: Pydantic model class describing the configuration fields. Set to None when no config is required.
    CONFIGURATION_ARGS = None

    def set_runtime_arguments(self, runtime_arguments: dict[str, Any]) -> None:
        """Populate class-level config fields from a dict of runtime values.

        Typically called as ``plugin.set_runtime_arguments({"configuration_args": {...}})``,
        which instantiates ``CONFIGURATION_ARGS`` with the provided dict and stores it as
        an instance attribute so ``self.CONFIGURATION_ARGS.<field>`` works throughout the plugin.
        """
        for key, value in runtime_arguments.items():
            class_field_key = key.upper()
            field = getattr(self, class_field_key)
            if field is None:
                continue
            setattr(self, class_field_key, field(**value))

    def get_config_schema(self) -> Any:
        """Return the JSON Schema for this plugin's configuration, derived from ``CONFIGURATION_ARGS``."""
        config_class = type(self).CONFIGURATION_ARGS
        if config_class is None:
            return {}
        return config_class.model_json_schema()
