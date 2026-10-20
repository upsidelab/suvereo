from unittest.mock import MagicMock

import pytest
from enthusiast_common.evaluation.trace import TraceRecorder

from agent.evaluation.integrations import EvalIntegrationPluginResolver
from agent.evaluation.run_context import EvalRunContext

from .greeter import GreeterIntegrationPlugin, GreeterMockIntegration, OtherIntegrationPlugin


@pytest.fixture
def mocks():
    return [GreeterMockIntegration(), GreeterMockIntegration()]


class TestEvalIntegrationPluginResolver:
    def test_resolves_the_latest_matching_mock(self, mocks):
        with EvalRunContext(TraceRecorder(), mocks).activate():
            resolver = EvalIntegrationPluginResolver()

            assert resolver.resolve(1, GreeterIntegrationPlugin) is mocks[-1]
            assert resolver.resolve_all(1, GreeterIntegrationPlugin) == mocks
            assert resolver.has_any(1, GreeterIntegrationPlugin)

    def test_real_integrations_are_refused_unless_the_run_allows_them(self, mocks):
        with EvalRunContext(TraceRecorder(), mocks).activate():
            resolver = EvalIntegrationPluginResolver()

            assert resolver.resolve(1, OtherIntegrationPlugin) is None
            assert resolver.resolve_all(1, OtherIntegrationPlugin) == []
            assert not resolver.has_any(1, OtherIntegrationPlugin)

    def test_uncovered_interfaces_fall_back_to_the_real_resolver_when_allowed(self, mocks):
        real = MagicMock()
        real.return_value.resolve.return_value = "real"
        real.return_value.resolve_all.return_value = ["real"]
        real.return_value.has_any.return_value = True

        with EvalRunContext(TraceRecorder(), mocks, real_resolver=real).activate():
            resolver = EvalIntegrationPluginResolver()

            assert resolver.resolve(1, OtherIntegrationPlugin) == "real"
            assert resolver.resolve_all(1, OtherIntegrationPlugin) == ["real"]
            assert resolver.has_any(1, OtherIntegrationPlugin)

    def test_a_covered_interface_never_reaches_the_real_resolver(self, mocks):
        real = MagicMock()

        with EvalRunContext(TraceRecorder(), mocks, real_resolver=real).activate():
            resolver = EvalIntegrationPluginResolver()

            assert resolver.resolve(1, GreeterIntegrationPlugin) is mocks[-1]
            assert resolver.resolve_all(1, GreeterIntegrationPlugin) == mocks
            assert resolver.has_any(1, GreeterIntegrationPlugin)

        real.return_value.resolve.assert_not_called()
        real.return_value.resolve_all.assert_not_called()
        real.return_value.has_any.assert_not_called()

    def test_outside_a_run_nothing_resolves(self):
        assert EvalIntegrationPluginResolver().resolve(1, GreeterIntegrationPlugin) is None
