from typing import Any, Optional

from enthusiast_common.integrations import BaseIntegrationPluginResolver
from enthusiast_common.integrations.base import IntegrationT

from agent.evaluation.run_context import EvalRunContext


class EvalIntegrationPluginResolver(BaseIntegrationPluginResolver):
    """Answers integration lookups from the current run's mocks; an interface no mock covers goes to the real resolver if the run allows it."""

    def resolve(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> Optional[IntegrationT]:
        mocks = self._mocks(plugin_base)
        if mocks:
            return mocks[-1]
        real = self._real()
        return real.resolve(data_set_id, plugin_base) if real else None

    def resolve_all(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> list[IntegrationT]:
        mocks = self._mocks(plugin_base)
        if mocks:
            return mocks
        real = self._real()
        return real.resolve_all(data_set_id, plugin_base) if real else []

    def has_any(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> bool:
        if self._mocks(plugin_base):
            return True
        real = self._real()
        return bool(real and real.has_any(data_set_id, plugin_base))

    @staticmethod
    def _mocks(plugin_base: type[IntegrationT]) -> list[IntegrationT]:
        context = EvalRunContext.current()
        return [i for i in context.integrations if isinstance(i, plugin_base)] if context else []

    @staticmethod
    def _real() -> BaseIntegrationPluginResolver | None:
        context = EvalRunContext.current()
        return context.real_resolver() if context and context.real_resolver else None
