from unittest.mock import MagicMock, patch

import pytest
from enthusiast_common.integrations import BaseIntegration, BaseSourceIntegrationManager
from model_bakery import baker

from catalog.integrations.registry import IntegrationManagerRegistry
from catalog.integrations.sync_service import IntegrationSyncService
from catalog.models import Integration

pytestmark = pytest.mark.django_db


class UnregisteredSourceManager(BaseSourceIntegrationManager):
    def sync(self, plugin, dataset_id, integration_id):
        pass


class UnregisteredSourceIntegration(BaseIntegration):
    """Not in CATALOG_INTEGRATION_PLUGINS, the way an evaluation's mock integration isn't."""

    TYPE = "unregistered_source"
    NAME = "Unregistered source"
    INTEGRATION_MANAGER = UnregisteredSourceManager


class NoDataIntegration(BaseIntegration):
    TYPE = "no_data"
    NAME = "No data"


class TestIntegrationSyncService:
    def test_sync_hands_the_plugin_to_its_manager(self):
        integration = baker.make(Integration)
        plugin = UnregisteredSourceIntegration()
        manager = MagicMock()

        with patch.object(IntegrationManagerRegistry, "get_manager_for", return_value=manager) as get_manager:
            synced = IntegrationSyncService().sync(plugin, integration)

        get_manager.assert_called_once_with(UnregisteredSourceManager)
        manager.sync.assert_called_once_with(plugin, integration.dataset_id, integration.id)
        assert synced is True

    def test_sync_skips_integrations_without_a_manager(self):
        integration = baker.make(Integration)

        with patch.object(IntegrationManagerRegistry, "get_manager_for", return_value=None):
            assert IntegrationSyncService().sync(NoDataIntegration(), integration) is False
