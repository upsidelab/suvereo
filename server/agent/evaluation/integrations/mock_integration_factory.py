from pathlib import Path

from django.utils.module_loading import import_string
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.mocks import BaseMockIntegration
from enthusiast_common.evaluation.suite import IntegrationConfig
from enthusiast_common.integrations import BaseIntegration
from pydantic import ValidationError


class MockIntegrationFactory:
    """Builds a fresh mock integration from a suite's integration config, with relative data paths resolved."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def build(self, config: IntegrationConfig) -> BaseMockIntegration:
        """A configured instance; raises EvalSuiteError for an unknown or non-mock class, or invalid config."""
        integration = self.integration_class(config)()
        try:
            integration.set_runtime_arguments({"configuration_args": config.config})
        except (ValidationError, TypeError) as e:
            raise EvalSuiteError(f"Invalid config for integration {config.key}: {e}") from e
        integration.base_dir = self.base_dir
        return integration

    def integration_class(self, config: IntegrationConfig) -> type[BaseMockIntegration]:
        """The mock integration class a config names, generating one for a plugin interface."""
        target = self._import(config.key)
        if config.class_path:
            if not (isinstance(target, type) and issubclass(target, BaseMockIntegration)):
                raise EvalSuiteError(
                    f"{config.class_path} is not a mock integration; real integrations are never mocked."
                )
            return target
        if not (isinstance(target, type) and issubclass(target, BaseIntegration)):
            raise EvalSuiteError(f"{config.interface} is not an integration interface.")
        return BaseMockIntegration.for_plugin_interface(target)

    @staticmethod
    def _import(path: str) -> object:
        try:
            return import_string(path)
        except ImportError as e:
            raise EvalSuiteError(f"Cannot import {path}: {e}") from e
