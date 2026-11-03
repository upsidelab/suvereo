from unittest.mock import patch

import pytest
from django.db import IntegrityError
from model_bakery import baker
from suvereo_common.integrations import BaseToolProvidingIntegration

from agent.models import Agent
from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.integrations.resolver import IntegrationPluginResolver
from catalog.models import Integration
from catalog.tests.integration_mocks import (
    MockMultiInstanceIntegration,
    MockSingleInstanceIntegration,
    MockToolProvidingIntegration,
)

pytestmark = pytest.mark.django_db


def _agent_selecting(data_set, *integrations) -> Agent:
    agent = baker.make(Agent, dataset=data_set, config={})
    agent.tool_providing_integrations.set(integrations)
    return agent


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
    return_value=[MockSingleInstanceIntegration, MockMultiInstanceIntegration, MockToolProvidingIntegration],
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

    def test_resolve_all_for_agent_returns_every_selected_match(self, _mock_get_plugin_classes, data_set):
        integration_kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        first = baker.make(Integration, **integration_kwargs, config={"marker": "first"})
        second = baker.make(Integration, **integration_kwargs, config={"marker": "second"})
        agent = _agent_selecting(data_set, first, second)

        result = IntegrationPluginResolver().resolve_all_for_agent(agent.id, MockMultiInstanceIntegration)

        assert {instance.CONFIGURATION_ARGS.marker for instance in result} == {"first", "second"}

    def test_resolve_all_for_agent_leaves_out_integrations_the_agent_did_not_select(
        self, _mock_get_plugin_classes, data_set
    ):
        integration_kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        selected = baker.make(Integration, **integration_kwargs, config={"marker": "selected"})
        baker.make(Integration, **integration_kwargs, config={"marker": "other"})
        agent = _agent_selecting(data_set, selected)

        result = IntegrationPluginResolver().resolve_all_for_agent(agent.id, MockMultiInstanceIntegration)

        assert [instance.CONFIGURATION_ARGS.marker for instance in result] == ["selected"]

    def test_resolve_all_for_agent_skips_a_record_whose_stored_config_is_invalid(
        self, _mock_get_plugin_classes, data_set
    ):
        integration_kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        broken = baker.make(Integration, **integration_kwargs, config={"marker": {"not": "a string"}})
        healthy = baker.make(Integration, **integration_kwargs, config={"marker": "healthy"})
        agent = _agent_selecting(data_set, broken, healthy)

        result = IntegrationPluginResolver().resolve_all_for_agent(agent.id, MockMultiInstanceIntegration)

        assert [instance.CONFIGURATION_ARGS.marker for instance in result] == ["healthy"]

    def test_has_any_for_agent_is_true_when_a_matching_integration_is_selected(
        self, _mock_get_plugin_classes, data_set, django_assert_num_queries
    ):
        integration = baker.make(Integration, dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        agent = _agent_selecting(data_set, integration)

        # Runs on every conversation turn, so it has to stay a single existence check.
        with django_assert_num_queries(1):
            assert IntegrationPluginResolver().has_any_for_agent(agent.id, MockMultiInstanceIntegration) is True

    def test_has_any_for_agent_is_false_when_nothing_is_selected(self, _mock_get_plugin_classes, data_set):
        baker.make(Integration, dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        agent = _agent_selecting(data_set)

        assert IntegrationPluginResolver().has_any_for_agent(agent.id, MockMultiInstanceIntegration) is False

    def test_has_any_for_agent_is_false_when_only_other_categories_are_selected(
        self, _mock_get_plugin_classes, data_set
    ):
        integration = baker.make(Integration, dataset=data_set, type="mock_single", allows_multiple_instances=False)
        agent = _agent_selecting(data_set, integration)

        assert IntegrationPluginResolver().has_any_for_agent(agent.id, MockMultiInstanceIntegration) is False

    def test_integration_ids_lists_the_data_sets_integrations_of_a_kind(self, _mock_get_plugin_classes, data_set):
        tools = baker.make(Integration, dataset=data_set, type="mock_tools", allows_multiple_instances=True)
        baker.make(Integration, dataset=data_set, type="mock_single")
        baker.make(Integration, type="mock_tools", allows_multiple_instances=True)

        assert IntegrationPluginResolver().ids_for_data_set(data_set.id, BaseToolProvidingIntegration) == [tools.id]

    def test_has_any_for_agent_does_not_read_stored_config(self, _mock_get_plugin_classes, data_set):
        """A record too broken to instantiate still counts — has_any_for_agent never builds the plugin."""
        integration = baker.make(
            Integration,
            dataset=data_set,
            type="mock_multi",
            allows_multiple_instances=True,
            config={"marker": {"not": "a string"}},
        )
        agent = _agent_selecting(data_set, integration)

        assert IntegrationPluginResolver().has_any_for_agent(agent.id, MockMultiInstanceIntegration) is True
