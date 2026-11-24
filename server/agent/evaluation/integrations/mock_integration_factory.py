from pathlib import Path

from django.utils.module_loading import import_string
from pydantic import ValidationError
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.mocks import BaseMockIntegration
from suvereo_common.evaluation.suite import IntegrationConfig
from suvereo_common.integrations import BaseIntegration


class MockIntegrationFactory:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def build(self, config: IntegrationConfig) -> BaseMockIntegration:
        integration_class = self.resolve_class(config)
        try:
            integration = integration_class()
        except TypeError as e:
            raise EvalSuiteError(f"Integration {config.key} cannot be built: {e}") from e
        try:
            integration.set_runtime_arguments({"configuration_args": config.config})
        except (ValidationError, TypeError) as e:
            raise EvalSuiteError(f"Invalid config for integration {config.key}: {e}") from e
        integration.base_dir = self.base_dir
        return integration

    def resolve_class(self, config: IntegrationConfig) -> type[BaseMockIntegration]:
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
