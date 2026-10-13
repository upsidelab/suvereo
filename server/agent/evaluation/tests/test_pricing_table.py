import pytest
from enthusiast_common.evaluation.suite import ModelPricing
from enthusiast_common.evaluation.trace import ExecutionTrace, LLMCall

from agent.evaluation.pricing_table import PricingTable


@pytest.fixture
def table():
    return PricingTable(
        {
            "gpt-4o": ModelPricing(input_per_million=2.5, output_per_million=10, cached_input_per_million=1.25),
            "gpt-4o-mini": ModelPricing(input_per_million=0.15, output_per_million=0.6),
        }
    )


class TestPricingTable:
    def test_the_shipped_table_loads_with_a_date(self):
        loaded = PricingTable.load()

        assert loaded.as_of
        assert loaded.price_for("claude-opus-5-5").output_per_million == 20.0

    @pytest.mark.parametrize(
        "model, expected",
        [
            ("gpt-4o", "gpt-4o"),
            ("gpt-4o-mini-2024-07-18", "gpt-4o-mini"),
            ("gpt-4o-2024-08-06", "gpt-4o"),
            ("gpt-4o-mini-20240718", "gpt-4o-mini"),
            ("gpt-4o-audio-preview", None),
            ("gpt-4o-mini-tts", None),
            ("llama-3", None),
        ],
    )
    def test_only_dated_snapshots_borrow_their_base_models_price(self, table, model, expected):
        price = table.price_for(model)

        assert price is (table.prices[expected] if expected else None)

    def test_cached_tokens_use_the_cached_rate_or_else_the_input_rate(self, table):
        cached_rate = LLMCall(run_id="a", requested_model="gpt-4o", input_tokens=1_000_000, cached_input_tokens=400_000)
        no_cached_rate = LLMCall(
            run_id="b", requested_model="gpt-4o-mini", input_tokens=1_000_000, cached_input_tokens=400_000
        )

        assert table.call_cost(cached_rate) == pytest.approx(0.6 * 2.5 + 0.4 * 1.25)
        assert table.call_cost(no_cached_rate) == pytest.approx(0.15)

    def test_cache_writes_use_the_cache_write_rate(self):
        table = PricingTable(
            {"claude": ModelPricing(input_per_million=4, output_per_million=20, cache_write_input_per_million=5)}
        )
        call = LLMCall(run_id="a", requested_model="claude", input_tokens=1_000_000, cache_write_input_tokens=600_000)

        assert table.call_cost(call) == pytest.approx(0.4 * 4 + 0.6 * 5)
        assert PricingTable.load().price_for("claude-opus-5-5").cache_write_input_per_million == 5.0

    def test_a_call_without_reported_usage_is_unpriced_rather_than_free(self, table):
        trace = ExecutionTrace(llm_calls=[LLMCall(run_id="a", requested_model="gpt-4o", usage_reported=False)])

        cost = table.trace_cost(trace)

        assert (cost.usd, cost.unpriced_models) == (None, ["gpt-4o (no token usage reported)"])

    def test_a_trace_with_an_unpriced_model_has_no_total(self, table):
        trace = ExecutionTrace(
            llm_calls=[
                LLMCall(run_id="a", requested_model="gpt-4o", output_tokens=1000),
                LLMCall(run_id="b", model="llama-3"),
            ]
        )

        cost = table.trace_cost(trace)

        assert (cost.usd, cost.unpriced_models) == (None, ["llama-3"])

    def test_overrides_replace_a_price(self, table):
        override = ModelPricing(input_per_million=1, output_per_million=1)

        assert table.with_overrides({"gpt-4o": override}).price_for("gpt-4o") == override
        assert table.price_for("gpt-4o").input_per_million == 2.5
