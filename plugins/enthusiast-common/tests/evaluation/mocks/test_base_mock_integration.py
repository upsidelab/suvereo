import pytest
from enthusiast_common.evaluation.mocks import BaseMockIntegration, MockConfigError, UnmockedCallError
from enthusiast_common.evaluation.trace import TraceRecorder

from .shop import Shop, ShopMock
from .shop_plugin import Catalog, ShopIntegrationManager, ShopIntegrationPlugin


def _configured(integration_class, **config):
    integration = integration_class()
    integration.set_runtime_arguments({"configuration_args": config})
    return integration


class ShopMockIntegration(BaseMockIntegration, ShopIntegrationPlugin):
    MOCK_CLASS = ShopMock

    def build_shop(self):
        return self.mock

    def build_catalog(self):
        return None

    def fetch(self):
        return self.config.data.get("rows", [])


class TestHandWrittenMockIntegration:
    def test_builds_its_mock_from_the_configured_behaviour_and_data(self):
        integration = _configured(
            ShopMockIntegration, behaviour={"create_order": {"returns": "ORD-{n}"}}, data={"rows": [{"sku": "a"}]}
        )

        assert integration.build_shop().create_order([]) == "ORD-1"
        assert integration.fetch() == [{"sku": "a"}]

    def test_the_mock_is_shared_so_every_caller_sees_the_same_calls(self):
        integration = ShopMockIntegration()

        integration.build_shop().get_product("x")

        assert integration.mock is integration.build_shop()
        assert [c.method for c in integration.mock.calls] == ["get_product"]

    def test_reset_mocks_starts_every_built_mock_afresh(self):
        integration = _configured(ShopMockIntegration, behaviour={"create_order": {"returns": "ORD-{n}"}})
        integration.build_shop().create_order([])

        integration.reset_mocks()

        assert integration.mock.calls == []
        assert integration.build_shop().create_order([]) == "ORD-1"

    def test_without_configuration_the_mock_has_no_behaviour(self):
        assert ShopMockIntegration().mock.get_product("x") is None

    def test_strict_applies_to_the_mock(self):
        with pytest.raises(UnmockedCallError):
            _configured(ShopMockIntegration, strict=True).mock.get_product("x")

    def test_a_behaviour_key_no_mock_has_is_rejected(self):
        integration = _configured(ShopMockIntegration, behaviour={"delete_everything": {"returns": None}})

        with pytest.raises(MockConfigError, match="delete_everything"):
            integration.build_shop()

    def test_the_recorder_reaches_mocks_built_before_and_after_it_is_set(self):
        integration = ShopMockIntegration()
        early = integration.mock
        recorder = TraceRecorder()

        integration.recorder = recorder
        early.get_product("x")

        assert [c.method for c in recorder.trace.mock_calls] == ["get_product"]


class TestGeneratedMockIntegration:
    @pytest.fixture
    def integration_class(self):
        return BaseMockIntegration.for_plugin_interface(ShopIntegrationPlugin)

    def test_is_one_cached_class_that_implements_the_plugin_interface(self, integration_class):
        assert BaseMockIntegration.for_plugin_interface(ShopIntegrationPlugin) is integration_class
        assert issubclass(integration_class, ShopIntegrationPlugin)
        assert issubclass(integration_class, BaseMockIntegration)
        assert integration_class.INTEGRATION_MANAGER is ShopIntegrationManager

    def test_builders_return_shared_mocks_of_their_return_types(self, integration_class):
        integration = _configured(
            integration_class,
            behaviour={"create_order": {"returns": "ORD-{n}"}, "list_skus": {"returns": ["SKU-1"]}},
        )

        shop, catalog = integration.build_shop(), integration.build_catalog()

        assert isinstance(shop, Shop) and isinstance(catalog, Catalog)
        assert integration.build_shop() is shop
        assert (shop.create_order([]), catalog.list_skus()) == ("ORD-1", ["SKU-1"])

    def test_other_abstract_methods_are_answered_by_a_mock_of_the_plugin_interface(self, integration_class):
        integration = _configured(integration_class, behaviour={"fetch": {"returns": [{"sku": "SKU-1"}]}})

        assert integration.fetch() == [{"sku": "SKU-1"}]

    def test_every_mock_records_into_the_same_trace(self, integration_class):
        integration = integration_class()
        integration.recorder = recorder = TraceRecorder()

        integration.build_shop().get_product("x")
        integration.build_catalog().list_skus()
        integration.fetch()

        assert [c.method for c in recorder.trace.mock_calls] == ["get_product", "list_skus", "fetch"]

    def test_a_behaviour_key_none_of_its_mocks_has_is_rejected(self, integration_class):
        integration = _configured(integration_class, behaviour={"list_sku": {"returns": []}})

        with pytest.raises(MockConfigError, match="list_sku"):
            integration.build_catalog()
