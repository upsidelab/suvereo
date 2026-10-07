import pytest
from enthusiast_common.evaluation.mocks import MockBehaviour
from pydantic import BaseModel, ValidationError


class Address(BaseModel):
    city: str


class TestMockBehaviour:
    @pytest.mark.parametrize(
        "declared",
        [
            {},
            {"returns": 1, "sequence": [1]},
            {"returns": 1, "raises": {"error": "ValueError"}},
            {"sequence": []},
            {"raises": None},
            {"sequence": None},
        ],
    )
    def test_needs_exactly_one_outcome(self, declared):
        with pytest.raises(ValidationError):
            MockBehaviour.model_validate(declared)

    def test_returning_none_is_an_outcome(self):
        assert MockBehaviour(returns=None).returns is None

    def test_without_when_it_matches_every_call(self):
        assert MockBehaviour(returns=1).matches({"sku": "anything"})

    def test_when_matches_named_arguments_only_if_all_are_equal(self):
        behaviour = MockBehaviour(returns=1, when={"sku": "SKU-1", "quantity": 2})

        assert behaviour.matches({"sku": "SKU-1", "quantity": 2, "email": None})
        assert not behaviour.matches({"sku": "SKU-1", "quantity": 3})
        assert not behaviour.matches({"sku": "SKU-1"})

    def test_when_compares_tuples_and_models_as_yaml_writes_them(self):
        behaviour = MockBehaviour(returns=1, when={"items": [["SKU-1", 2]], "address": {"city": "Krakow"}})

        assert behaviour.matches({"items": [("SKU-1", 2)], "address": Address(city="Krakow")})
