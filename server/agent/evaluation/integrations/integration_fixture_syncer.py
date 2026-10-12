from enthusiast_common.evaluation.mocks import BaseMockIntegration

from catalog.integrations.sync_service import IntegrationSyncService
from catalog.models import DataSet, Integration


class IntegrationFixtureSyncer:
    """Loads a mock integration's fixture data into a sandbox DataSet through the integration's own sync manager."""

    def sync(self, integration: BaseMockIntegration, data_set: DataSet) -> Integration:
        """Record the integration on the DataSet and sync it now; integrations without a manager just get the record."""
        record = Integration.objects.create(
            dataset=data_set,
            type=integration.TYPE,
            config=integration.config.model_dump(),
            allows_multiple_instances=True,
        )
        IntegrationSyncService().sync(integration, record)
        return record
