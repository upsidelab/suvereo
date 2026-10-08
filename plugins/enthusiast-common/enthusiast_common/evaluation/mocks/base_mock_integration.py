import inspect
import typing
from typing import Any, ClassVar

from ...integrations import BaseIntegration
from ..trace import TraceRecorder
from .base_mock import BaseMock
from .errors import MockConfigError
from .mock_integration_config import MockIntegrationConfig

BUILDER_PREFIX = "build_"


class BaseMockIntegration(BaseIntegration):
    """An integration whose external systems are mocks, one shared mock per interface for the whole run."""

    CONFIGURATION_ARGS = MockIntegrationConfig
    MOCK_CLASS: ClassVar[type[BaseMock]]

    _generated: ClassVar[dict[type, type["BaseMockIntegration"]]] = {}

    def __init__(self):
        self._recorder: TraceRecorder | None = None
        self._mocks: dict[type[BaseMock], BaseMock] = {}

    @classmethod
    def for_plugin_interface(cls, plugin_interface: type[BaseIntegration]) -> type["BaseMockIntegration"]:
        """A mock integration for a plugin interface: each build_* returns a mock of its return type, other abstract methods a mock of the interface."""
        if plugin_interface not in BaseMockIntegration._generated:
            BaseMockIntegration._generated[plugin_interface] = cls._generate(plugin_interface)
        return BaseMockIntegration._generated[plugin_interface]

    @classmethod
    def mock_classes(cls) -> tuple[type[BaseMock], ...]:
        """The mock classes this integration provides; behaviour keys must be methods of at least one."""
        return (cls.MOCK_CLASS,)

    @property
    def config(self) -> MockIntegrationConfig:
        """The configuration set through ``set_runtime_arguments``, or an empty one before that."""
        configured = self.CONFIGURATION_ARGS
        return configured if isinstance(configured, MockIntegrationConfig) else MockIntegrationConfig()

    @property
    def recorder(self) -> TraceRecorder | None:
        """Where every mock records its calls; setting it also reaches mocks already built."""
        return self._recorder

    @recorder.setter
    def recorder(self, recorder: TraceRecorder | None) -> None:
        self._recorder = recorder
        for mock in self._mocks.values():
            mock.recorder = recorder

    @property
    def mock(self) -> BaseMock:
        """The run's shared instance of ``MOCK_CLASS``."""
        return self.mock_for(self.MOCK_CLASS)

    def mock_for(self, mock_class: type[BaseMock]) -> BaseMock:
        """The run's shared instance of one of this integration's mock classes; raises MockConfigError for a behaviour key no mock has."""
        if mock_class not in self._mocks:
            self._check_behaviour()
            config = self.config
            methods = mock_class.interface_methods()
            behaviour = {name: value for name, value in config.behaviour.items() if name in methods}
            self._mocks[mock_class] = mock_class(behaviour, config.data, config.strict, self._recorder)
        return self._mocks[mock_class]

    def _check_behaviour(self) -> None:
        known = {name for mock_class in self.mock_classes() for name in mock_class.interface_methods()}
        if unknown := sorted(set(self.config.behaviour) - known):
            raise MockConfigError(
                f"{type(self).__name__} mocks no method named {', '.join(unknown)}; it mocks: {', '.join(sorted(known))}."
            )

    @classmethod
    def _generate(cls, plugin_interface: type[BaseIntegration]) -> type["BaseMockIntegration"]:
        builders, forwarded = {}, []
        for name in sorted(getattr(plugin_interface, "__abstractmethods__", ())):
            built = cls._built_type(getattr(plugin_interface, name)) if name.startswith(BUILDER_PREFIX) else None
            if built is not None:
                builders[name] = BaseMock.declarative(built)
            else:
                forwarded.append(name)

        interface_mock = BaseMock.declarative(plugin_interface) if forwarded else None
        mock_classes = (*builders.values(), *([interface_mock] if interface_mock else []))
        namespace: dict[str, Any] = {
            "TYPE": f"mock_{plugin_interface.__name__}",
            "NAME": f"Mock {plugin_interface.__name__}",
            "mock_classes": classmethod(lambda _cls: mock_classes),
            **{name: cls._builder(mock_class) for name, mock_class in builders.items()},
            **{name: cls._forwarder(name, interface_mock) for name in forwarded},
        }
        return type(f"Mock{plugin_interface.__name__}", (cls, plugin_interface), namespace)

    @staticmethod
    def _built_type(method: Any) -> type | None:
        try:
            built = typing.get_type_hints(method).get("return")
        except (NameError, TypeError):
            built = inspect.signature(method).return_annotation
        return built if inspect.isclass(built) else None

    @staticmethod
    def _builder(mock_class: type[BaseMock]) -> Any:
        def build(self):
            return self.mock_for(mock_class)

        return build

    @staticmethod
    def _forwarder(name: str, mock_class: type[BaseMock]) -> Any:
        def method(self, *args, **kwargs):
            return getattr(self.mock_for(mock_class), name)(*args, **kwargs)

        method.__name__ = name
        return method
