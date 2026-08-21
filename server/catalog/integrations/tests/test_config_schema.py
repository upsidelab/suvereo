from unittest.mock import patch

import pytest
from model_bakery import baker
from pydantic import BaseModel, Field

from catalog.models import DataSet, Integration
from catalog.serializers import IntegrationSerializer

pytestmark = pytest.mark.django_db


class DummyConfig(BaseModel):
    store_url: str = Field(title="Store URL", description="Where the shop lives")
    page_size: int = 50


class DummyPlugin:
    TYPE = "dummy"
    NAME = "Dummy"
    INTEGRATION_TYPE_NAME = "E-commerce"
    CONFIGURATION_ARGS = DummyConfig

    @classmethod
    def is_syncable(cls):
        return True

    def get_config_schema(self):
        return DummyConfig.model_json_schema()


class UnconfigurablePlugin(DummyPlugin):
    CONFIGURATION_ARGS = None

    def get_config_schema(self):
        return {}


@pytest.fixture
def integration():
    return baker.make(
        Integration,
        dataset=baker.make(DataSet),
        type="dummy",
        config={"store_url": "https://shop.example"},
    )


def _serialize(integration, plugin_class=DummyPlugin):
    with patch(
        "catalog.integrations.registry.IntegrationPluginRegistry.get_plugin_class_by_type",
        return_value=plugin_class,
    ):
        return IntegrationSerializer(integration).data


class TestIntegrationConfigSchema:
    def test_serves_the_schema_the_plugin_declares(self, integration):
        assert _serialize(integration)["config_schema"] == DummyConfig.model_json_schema()

    def test_the_schema_names_the_required_fields_and_their_titles(self, integration):
        schema = _serialize(integration)["config_schema"]

        assert schema["required"] == ["store_url"]
        assert schema["properties"]["store_url"]["title"] == "Store URL"
        assert schema["properties"]["store_url"]["description"] == "Where the shop lives"

    def test_a_plugin_with_no_configuration_has_an_empty_schema(self, integration):
        assert _serialize(integration, UnconfigurablePlugin)["config_schema"] == {}

    def test_an_integration_whose_plugin_is_gone_has_an_empty_schema(self, integration):
        with patch(
            "catalog.integrations.registry.IntegrationPluginRegistry.get_plugin_class_by_type",
            side_effect=KeyError("dummy"),
        ):
            assert IntegrationSerializer(integration).data["config_schema"] == {}
