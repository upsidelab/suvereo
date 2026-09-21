from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

from enthusiast_common.indexing import BaseEntityIndexer
from langchain_core.tools import BaseTool as LCBaseTool


class BaseIntegrationManager(ABC):
    """Marker base for a category of integrations."""


class BaseSourceIntegrationManager(BaseIntegrationManager):
    """Marker for integration categories whose plugins pull data from an external source."""

    def __init__(self, indexer: BaseEntityIndexer):
        """The framework host injects the indexer used to embed synced entities."""
        self._indexer = indexer

    @abstractmethod
    def sync(self, plugin: Any, dataset_id: Any, integration_id: Any) -> None:
        """Pull data from the plugin's external source into the DataSet."""


class BaseIntegration(ABC):
    """A connection to one external system, declared by a vertical.

    The framework stores the integration's configuration and instantiates the
    plugin with that config before use. A DataSet holds at most one integration
    of a given ``TYPE``, unless the type opts into ``ALLOWS_MULTIPLE_INSTANCES``.
    A vertical may add further capabilities in its own subclass; the base only
    covers configuration and how an instance presents itself.
    """

    #: Stable identifier for this integration type. Unique per DataSet unless ALLOWS_MULTIPLE_INSTANCES is True.
    TYPE: str
    #: Human-readable name shown in the UI.
    NAME: str
    #: Human-readable category label shown in the UI. Verticals override this on their plugin ABCs.
    INTEGRATION_TYPE_NAME: str = "Basic integration"
    #: Category this integration belongs to. Verticals set this on their plugin ABCs.
    INTEGRATION_MANAGER: type[BaseIntegrationManager] | None = None
    #: Pydantic model class describing the configuration fields. Set to None when no config is required.
    CONFIGURATION_ARGS = None
    #: When True, a DataSet may hold more than one integration of this TYPE. Defaults to False so
    #: every existing plugin stays capped at one; a type opts in by overriding this.
    ALLOWS_MULTIPLE_INSTANCES: bool = False

    @classmethod
    def is_syncable(cls) -> bool:
        """An integration is syncable when its manager pulls data from an external source."""
        return cls.INTEGRATION_MANAGER is not None and issubclass(cls.INTEGRATION_MANAGER, BaseSourceIntegrationManager)

    def instance_name(self) -> str:
        """Label for this configured instance, shown wherever integrations are listed.

        Defaults to the type's ``NAME``, which reads fine while a DataSet holds only one of each.
        A type allowing several instances should override this to include whatever distinguishes
        them — otherwise every one of them shows up under the same label.
        """
        return self.NAME

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


class BaseToolProvidingIntegration(BaseIntegration):
    """An integration that can also hand agents extra tools to call, on top of its stored config.

    Discovered generically via ``resolve_all(data_set_id, BaseToolProvidingIntegration)`` — the
    framework never needs to know about a specific tool-providing integration type (e.g. MCP
    servers); it only needs to know this capability exists.
    """

    @abstractmethod
    async def get_tools(self) -> list[LCBaseTool]:
        """Return the LangChain tools this integration instance currently makes available."""


# Bound to BaseIntegration, defined above — kept local to its only use below
# rather than hoisted to the top of the file with the other imports.
IntegrationT = TypeVar("IntegrationT", bound=BaseIntegration)


class BaseIntegrationPluginResolver(ABC):
    """Resolves the integration plugin configured for a data set.

    The framework host implements the lookup against its integration storage and
    declares the implementation in the default agent config, so plugin packages
    can locate integrations without knowing how the host stores them.
    """

    @abstractmethod
    def resolve(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> Optional[IntegrationT]:
        """Return a configured plugin instance of *plugin_base* for the data set, or None."""

    @abstractmethod
    def resolve_all(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> list[IntegrationT]:
        """Return every configured plugin instance of *plugin_base* for the data set.

        Best-effort: an implementation skips records it cannot instantiate (an unknown type, or a
        stored config that no longer validates) rather than raising, so that one broken integration
        does not hide the healthy ones from the caller.
        """

    @abstractmethod
    def has_any(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> bool:
        """Return whether the data set has at least one integration of *plugin_base*.

        Answers the question without instantiating plugins or reading their stored config, so it
        stays cheap enough to call on every conversation turn.
        """
