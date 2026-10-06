from unittest.mock import patch

import pytest
from django.db import IntegrityError
from model_bakery import baker

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.integrations.resolver import IntegrationPluginResolver
from catalog.models import Integration
from catalog.tests.integration_mocks import MockMultiInstanceIntegration, MockSingleInstanceIntegration

pytestmark = pytest.mark.django_db


class TestIntegrationUniqueConstraint:
    def test_second_capped_integration_of_same_type_raises_integrity_error(self, data_set):
        baker.make(Integration, dataset=data_set, type="mock_single", allows_multiple_instances=False)

        with pytest.raises(IntegrityError):
            Integration.objects.create(dataset=data_set, type="mock_single", allows_multiple_instances=False)

    def test_second_multi_instance_integration_of_same_type_succeeds(self, data_set):
        baker.make(Integration, dataset=data_set, type="mock_multi", allows_multiple_instances=True)

        Integration.objects.create(dataset=data_set, type="mock_multi", allows_multiple_instances=True)

        assert Integration.objects.filter(dataset=data_set, type="mock_multi").count() == 2


@patch.object(
    IntegrationPluginRegistry,
    "get_plugin_classes",
    return_value=[MockSingleInstanceIntegration, MockMultiInstanceIntegration],
)
class TestIntegrationPluginResolver:
    """Both mock plugins stand in for the registered set, so the resolver picks matching types out
    of it exactly as it would from CATALOG_INTEGRATION_PLUGINS."""

    def test_resolve_returns_only_the_latest_added_match(self, _mock_get_plugin_classes, data_set):
        integration_kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        baker.make(Integration, **integration_kwargs, config={"marker": "first"})
        baker.make(Integration, **integration_kwargs, config={"marker": "second"})

        result = IntegrationPluginResolver().resolve(data_set.id, MockMultiInstanceIntegration)

        assert result.CONFIGURATION_ARGS.marker == "second"

    def test_resolve_ignores_integrations_of_another_category(self, _mock_get_plugin_classes, data_set):
        baker.make(Integration, dataset=data_set, type="mock_single", allows_multiple_instances=False)

        assert IntegrationPluginResolver().resolve(data_set.id, MockMultiInstanceIntegration) is None

    def test_resolve_all_returns_every_match(self, _mock_get_plugin_classes, data_set):
        integration_kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        baker.make(Integration, **integration_kwargs, config={"marker": "first"})
        baker.make(Integration, **integration_kwargs, config={"marker": "second"})

        result = IntegrationPluginResolver().resolve_all(data_set.id, MockMultiInstanceIntegration)

        assert {instance.CONFIGURATION_ARGS.marker for instance in result} == {"first", "second"}

    def test_resolve_all_skips_a_record_whose_stored_config_is_invalid(self, _mock_get_plugin_classes, data_set):
        integration_kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        baker.make(Integration, **integration_kwargs, config={"marker": {"not": "a string"}})
        baker.make(Integration, **integration_kwargs, config={"marker": "healthy"})

        result = IntegrationPluginResolver().resolve_all(data_set.id, MockMultiInstanceIntegration)

        assert [instance.CONFIGURATION_ARGS.marker for instance in result] == ["healthy"]

    def test_has_any_is_true_when_a_matching_integration_exists(
        self, _mock_get_plugin_classes, data_set, django_assert_num_queries
    ):
        baker.make(Integration, dataset=data_set, type="mock_multi", allows_multiple_instances=True)

        # Runs on every conversation turn, so it has to stay a single existence check.
        with django_assert_num_queries(1):
            assert IntegrationPluginResolver().has_any(data_set.id, MockMultiInstanceIntegration) is True

    def test_has_any_is_false_when_only_other_categories_are_configured(self, _mock_get_plugin_classes, data_set):
        baker.make(Integration, dataset=data_set, type="mock_single", allows_multiple_instances=False)

        assert IntegrationPluginResolver().has_any(data_set.id, MockMultiInstanceIntegration) is False

    def test_has_any_does_not_read_stored_config(self, _mock_get_plugin_classes, data_set):
        """A record too broken to instantiate still counts — has_any never builds the plugin."""
        baker.make(
            Integration,
            dataset=data_set,
            type="mock_multi",
            allows_multiple_instances=True,
            config={"marker": {"not": "a string"}},
        )

        assert IntegrationPluginResolver().has_any(data_set.id, MockMultiInstanceIntegration) is True
