import asyncio
from unittest.mock import patch

import pytest
from model_bakery import baker

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration
from catalog.tests.integration_mocks import MockOAuthIntegration, MockSingleInstanceIntegration

# The writer persists from another thread, and so another connection: it cannot see rows held
# in an uncommitted test transaction, and its own write would not be visible back here.
pytestmark = pytest.mark.django_db(transaction=True)


class TestBuildInstanceHandsOverAConfigWriter:
    """Renewal is worthless if what it renews cannot be kept; this is the seam that keeps it."""

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_plugin_that_renews_is_given_a_way_to_persist(self, mock_class, data_set):
        mock_class.return_value = MockOAuthIntegration
        integration = baker.make(Integration, dataset=data_set, type="mock_oauth", config={"url": "https://x/mcp"})

        plugin = IntegrationPluginRegistry().build_instance(integration)

        assert plugin._config_writer is not None

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_what_it_writes_reaches_the_database(self, mock_class, data_set):
        mock_class.return_value = MockOAuthIntegration
        integration = baker.make(Integration, dataset=data_set, type="mock_oauth", config={"url": "https://x/mcp"})
        plugin = IntegrationPluginRegistry().build_instance(integration)

        asyncio.run(plugin._config_writer({"auth_token": "Bearer renewed"}))

        integration.refresh_from_db()
        assert integration.config["auth_token"] == "Bearer renewed"
        assert integration.config["url"] == "https://x/mcp"

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_plugin_that_never_renews_is_left_alone(self, mock_class, data_set):
        mock_class.return_value = MockSingleInstanceIntegration
        integration = baker.make(Integration, dataset=data_set, type="mock_single", config={})

        plugin = IntegrationPluginRegistry().build_instance(integration)

        assert not hasattr(plugin, "_config_writer")

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_a_deleted_integration_is_not_resurrected(self, mock_class, data_set):
        """A renewal can finish after the admin removed the server; it must not write it back."""
        mock_class.return_value = MockOAuthIntegration
        integration = baker.make(Integration, dataset=data_set, type="mock_oauth", config={"url": "https://x/mcp"})
        plugin = IntegrationPluginRegistry().build_instance(integration)
        pk = integration.pk
        integration.delete()

        asyncio.run(plugin._config_writer({"auth_token": "Bearer renewed"}))

        assert not Integration.objects.filter(pk=pk).exists()
