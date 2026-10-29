from pathlib import Path

import pytest
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.suite import IntegrationConfig

from agent.evaluation.integrations import MockIntegrationFactory

from .greeter import Greeter, GreeterIntegrationPlugin, GreeterMockIntegration

MODULE = Greeter.__module__


def _config(**fields) -> IntegrationConfig:
    return IntegrationConfig.model_validate(fields)


class TestMockIntegrationFactory:
    def test_builds_a_named_mock_integration_with_its_config_and_base_dir(self, tmp_path):
        integration = MockIntegrationFactory(tmp_path).build(
            _config(
                **{
                    "class": f"{MODULE}.GreeterMockIntegration",
                    "config": {"behaviour": {"greet": {"returns": "Hi {name}"}}},
                }
            )
        )

        assert isinstance(integration, GreeterMockIntegration)
        assert integration.base_dir == tmp_path
        assert integration.build_greeter().greet("Ann") == "Hi Ann"

    def test_generates_a_mock_integration_for_a_plugin_interface(self):
        integration = MockIntegrationFactory(Path.cwd()).build(_config(interface=f"{MODULE}.GreeterIntegrationPlugin"))

        assert isinstance(integration, GreeterIntegrationPlugin)
        assert isinstance(integration.build_greeter(), Greeter)

    def test_each_build_is_a_fresh_instance(self):
        factory = MockIntegrationFactory(Path.cwd())
        config = _config(**{"class": f"{MODULE}.GreeterMockIntegration"})

        assert factory.build(config) is not factory.build(config)

    @pytest.mark.parametrize(
        "fields, message",
        [
            ({"class": f"{MODULE}.RealGreeterIntegration"}, "not a mock integration"),
            ({"class": f"{MODULE}.Greeter"}, "not a mock integration"),
            ({"interface": f"{MODULE}.Greeter"}, "not an integration interface"),
            ({"class": f"{MODULE}.Nope"}, "Cannot import"),
            ({"class": f"{MODULE}.GreeterMockIntegration", "config": {"unknown": 1}}, "Invalid config"),
            ({"class": f"{MODULE}.IncompleteGreeterMockIntegration"}, "cannot be built"),
        ],
    )
    def test_unusable_configs_are_reported(self, fields, message):
        with pytest.raises(EvalSuiteError, match=message):
            MockIntegrationFactory(Path.cwd()).build(_config(**fields))
