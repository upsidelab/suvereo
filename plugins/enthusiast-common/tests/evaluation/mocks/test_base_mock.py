import asyncio
import inspect
from decimal import InvalidOperation
from unittest.mock import patch

import pytest
from enthusiast_common.evaluation.mocks import BaseMock, MockConfigError, UnmockedCallError
from enthusiast_common.evaluation.trace import TraceRecorder

from .shop import Shop, ShopError, ShopMock


class TestBaseMockOutcomes:
    def test_returns_a_declared_value(self):
        mock = ShopMock({"get_product": {"returns": {"sku": "SKU-1", "price": 10}}})

        assert mock.get_product("SKU-1") == {"sku": "SKU-1", "price": 10}

    def test_string_values_are_templates_over_the_call(self):
        mock = ShopMock(
            {
                "create_order": {"returns": "ORD-{n}"},
                "get_product": {"returns": {"sku": "{sku}", "label": "call {n} of {args[0]}"}},
            }
        )

        assert [mock.create_order([]), mock.create_order([])] == ["ORD-1", "ORD-2"]
        assert mock.get_product("SKU-7") == {"sku": "SKU-7", "label": "call 1 of SKU-7"}

    def test_braces_that_are_not_placeholders_stay_literal(self):
        mock = ShopMock({"get_product": {"returns": '{"id": 1} and {n:03d} and a lone { brace'}})

        assert mock.get_product("x") == '{"id": 1} and 001 and a lone { brace'

    def test_call_number_and_raw_arguments_win_over_parameters_with_the_same_name(self):
        mock = ShopMock({"search": {"returns": "call {n}, limit {args[1]}"}})

        assert mock.search("mug", 25) == "call 1, limit 25"

    def test_keyword_catchall_arguments_are_matched_and_templated_by_name(self):
        mock = ShopMock({"search": [{"when": {"colour": "red"}, "returns": ["{colour} mug"]}, {"returns": []}]})

        assert mock.search("mug", colour="red") == ["red mug"]
        assert mock.search("mug", colour="blue") == []

    def test_a_sequence_returns_one_value_per_call_and_repeats_the_last(self):
        mock = ShopMock({"get_product": {"sequence": [None, {"sku": "SKU-1"}]}})

        assert [mock.get_product("x") for _ in range(3)] == [None, {"sku": "SKU-1"}, {"sku": "SKU-1"}]

    @pytest.mark.parametrize(
        "error, expected",
        [("ShopError", ShopError), ("ValueError", ValueError), ("decimal.InvalidOperation", InvalidOperation)],
    )
    def test_raises_a_known_builtin_or_dotted_error(self, error, expected):
        mock = ShopMock({"create_order": {"raises": {"error": error, "message": "Out of stock: {items}"}}})

        with pytest.raises(expected, match=r"Out of stock: \['SKU-1'\]"):
            mock.create_order(["SKU-1"])

    def test_the_first_matching_behaviour_wins(self):
        mock = ShopMock(
            {
                "get_product": [
                    {"when": {"sku": "SKU-1"}, "returns": {"sku": "SKU-1"}},
                    {"when": {"sku": "SKU-2"}, "raises": {"error": "LookupError"}},
                    {"returns": None},
                ]
            }
        )

        assert mock.get_product("SKU-1") == {"sku": "SKU-1"}
        assert mock.get_product(sku="SKU-9") is None
        with pytest.raises(LookupError):
            mock.get_product("SKU-2")

    def test_latency_in_an_async_method_does_not_block_the_event_loop(self):
        mock = ShopMock({"ping": {"returns": True, "latency_ms": 250}})

        with (
            patch("enthusiast_common.evaluation.mocks.base_mock.asyncio.sleep") as async_sleep,
            patch("enthusiast_common.evaluation.mocks.base_mock.time.sleep") as blocking_sleep,
        ):
            async_sleep.return_value = None
            assert asyncio.run(mock.ping()) is True

        async_sleep.assert_called_once_with(0.25)
        blocking_sleep.assert_not_called()

    def test_latency_is_simulated(self):
        mock = ShopMock({"get_product": {"returns": None, "latency_ms": 250}})

        with patch("enthusiast_common.evaluation.mocks.base_mock.time.sleep") as sleep:
            mock.get_product("x")

        sleep.assert_called_once_with(0.25)

    def test_an_undeclared_call_returns_none_or_raises_when_strict(self):
        assert ShopMock().get_product("x") is None
        with pytest.raises(UnmockedCallError, match="Shop.get_product"):
            ShopMock(strict=True).get_product("x")


class TestBaseMockRecording:
    def test_every_call_is_recorded_including_errors(self):
        recorder = TraceRecorder()
        mock = ShopMock({"create_order": {"raises": {"error": "ShopError", "message": "down"}}}, recorder=recorder)

        mock.get_product("SKU-1")
        with pytest.raises(ShopError):
            mock.create_order([("SKU-1", 2)], email="a@b.c")

        get, create = mock.calls
        assert (get.method, get.args, get.result, get.error) == ("get_product", ["SKU-1"], None, None)
        assert create.arguments == {"items": [("SKU-1", 2)], "email": "a@b.c"}
        assert (create.args, create.kwargs, create.error) == ([[("SKU-1", 2)]], {"email": "a@b.c"}, "ShopError: down")
        assert recorder.trace.mock_calls == mock.calls
        assert mock.calls_to("create_order") == [create]

    def test_a_call_with_arguments_the_interface_rejects_is_recorded_and_raised(self):
        recorder = TraceRecorder()
        mock = ShopMock(recorder=recorder)

        with pytest.raises(TypeError):
            mock.get_product(skuu="x")

        assert mock.calls[0].method == "get_product"
        assert mock.calls[0].error.startswith("TypeError")
        assert recorder.trace.mock_calls == mock.calls

    def test_reset_forgets_calls_and_restarts_numbering(self):
        mock = ShopMock({"create_order": {"returns": "ORD-{n}"}, "get_product": {"sequence": [1, 2]}})
        mock.create_order([])
        mock.get_product("x")

        mock.reset()

        assert mock.calls == []
        assert (mock.create_order([]), mock.get_product("x")) == ("ORD-1", 1)


class TestBaseMockConfiguration:
    @pytest.mark.parametrize(
        "behaviour, message",
        [
            ({"delete_everything": {"returns": None}}, "no method 'delete_everything'"),
            ({"currencies": {"returns": []}}, "no method 'currencies'"),
            ({"get_product": {"returns": 1, "raises": {"error": "ValueError"}}}, "Invalid behaviour for 'get_product'"),
            ({"get_product": {"raises": {"error": "NoSuchError"}}}, "Unknown error 'NoSuchError'"),
            ({"get_product": {"raises": {"error": "no.such.module.Error"}}}, "Cannot import"),
            ({"get_product": {"when": {"skuu": "x"}, "returns": 1}}, "names skuu, which it does not take"),
        ],
    )
    def test_invalid_behaviour_fails_when_the_mock_is_built(self, behaviour, message):
        with pytest.raises(MockConfigError, match=message):
            ShopMock(behaviour)

    def test_when_may_name_any_argument_of_a_method_with_a_keyword_catchall(self):
        ShopMock({"search": {"when": {"anything": 1}, "returns": []}})

    def test_a_template_naming_an_unknown_value_is_reported(self):
        mock = ShopMock({"get_product": {"returns": "{nope}"}})

        with pytest.raises(MockConfigError, match=r"cannot fill \{nope\}"):
            mock.get_product("x")


class TestBaseMockInterface:
    def test_the_mock_passes_for_the_interface_and_keeps_its_signatures(self):
        mock = ShopMock()

        assert isinstance(mock, Shop)
        assert list(inspect.signature(ShopMock.create_order).parameters) == ["self", "items", "email"]
        assert mock.describe() is None
        assert asyncio.run(mock.ping()) is None

    def test_a_method_defined_on_the_mock_is_kept(self):
        class CountingShopMock(ShopMock):
            def create_order(self, items, email=None):
                return self._handle_call("create_order", (items,), {"email": email}) or f"ORD-{len(items)}"

        assert CountingShopMock().create_order(["a", "b"]) == "ORD-2"

    def test_default_can_hold_state_across_calls(self):
        class CatalogShopMock(ShopMock):
            def _answer_unmatched_call(self, method, arguments):
                if method == "get_product":
                    return self.data["catalog"].get(arguments["sku"])
                return super()._answer_unmatched_call(method, arguments)

        mock = CatalogShopMock({"create_order": {"returns": "ORD-1"}}, data={"catalog": {"SKU-1": {"price": 5}}})

        assert mock.get_product("SKU-1") == {"price": 5}
        assert mock.get_product("SKU-2") is None
        assert mock.create_order([]) == "ORD-1"

    def test_declarative_builds_one_mock_class_per_interface(self):
        mock_class = BaseMock.declarative(Shop)

        assert BaseMock.declarative(Shop) is mock_class
        assert mock_class({"get_product": {"returns": 3}}).get_product("x") == 3

    def test_an_interface_method_clashing_with_the_mock_is_rejected(self):
        class Clashing(Shop):
            def reset(self): ...

        with pytest.raises(TypeError, match="reset"):
            BaseMock.declarative(Clashing)
