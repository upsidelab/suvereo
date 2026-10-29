import re
from pathlib import Path

import yaml
from pydantic import BaseModel
from suvereo_common.evaluation.suite import ModelPricing
from suvereo_common.evaluation.trace import ExecutionTrace, LLMCall

DEFAULT_TABLE = Path(__file__).with_name("pricing.yaml")
TOKENS_PER_MILLION = 1_000_000
DATED_SNAPSHOT = re.compile(r"-(\d{4}-\d{2}-\d{2}|\d{8})$")


class TraceCost(BaseModel):
    """What a trace's LLM calls cost; usd is None when any call can't be priced, priced_usd sums the calls that can.

    unpriced_models have no price; models_without_usage answered without token counts, so their calls can't be priced.
    """

    usd: float | None
    priced_usd: float = 0.0
    unpriced_models: list[str] = []
    models_without_usage: list[str] = []


class PricingTable:
    """USD prices per model, from pricing.yaml with a suite's overrides on top."""

    def __init__(self, prices: dict[str, ModelPricing], as_of: str = ""):
        self.prices = prices
        self.as_of = as_of

    @classmethod
    def load(cls, path: Path = DEFAULT_TABLE) -> "PricingTable":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        prices = {
            name: ModelPricing(
                input_per_million=p["input"],
                output_per_million=p["output"],
                cached_input_per_million=p.get("cached_input"),
                cache_write_5m_input_per_million=p.get("cache_write_5m"),
                cache_write_1h_input_per_million=p.get("cache_write_1h"),
            )
            for name, p in data["models"].items()
        }
        return cls(prices, str(data.get("as_of", "")))

    def with_overrides(self, overrides: dict[str, ModelPricing]) -> "PricingTable":
        """A copy with some models' prices replaced, e.g. from a suite's models[].pricing."""
        return PricingTable({**self.prices, **overrides}, self.as_of)

    def price_for(self, model: str | None) -> ModelPricing | None:
        """The price for a model, or for the base of a dated snapshot (gpt-4o-mini-2024-07-18); variants are unpriced."""
        if not model:
            return None
        if model in self.prices:
            return self.prices[model]
        base = DATED_SNAPSHOT.sub("", model)
        return self.prices.get(base) if base != model else None

    def call_cost(self, call: LLMCall) -> float | None:
        """One call's USD cost; None when its model has no price or the provider reported no token counts."""
        price = self._price_of(call)
        if price is None or not call.usage_reported:
            return None
        cached = min(call.cached_input_tokens, call.input_tokens)
        written_5m = min(call.cache_write_5m_input_tokens, call.input_tokens - cached)
        written_1h = min(call.cache_write_1h_input_tokens, call.input_tokens - cached - written_5m)
        return (
            (call.input_tokens - cached - written_5m - written_1h) * price.input_per_million
            + cached * self._or_input_rate(price.cached_input_per_million, price)
            + written_5m * self._or_input_rate(price.cache_write_5m_input_per_million, price)
            + written_1h * self._or_input_rate(price.cache_write_1h_input_per_million, price)
            + call.output_tokens * price.output_per_million
        ) / TOKENS_PER_MILLION

    def trace_cost(self, trace: ExecutionTrace) -> TraceCost:
        """The trace's total cost, or None with the unpriced model names if any call cannot be priced."""
        costs = [(call, self.call_cost(call)) for call in trace.llm_calls]
        unpriced = sorted({self._model_name(c) for c in trace.llm_calls if self._price_of(c) is None})
        without_usage = sorted({self._model_name(c) for c in trace.llm_calls if not c.usage_reported})
        return TraceCost(
            usd=None if unpriced or without_usage else sum(cost for _, cost in costs),
            priced_usd=sum(cost for _, cost in costs if cost is not None),
            unpriced_models=unpriced,
            models_without_usage=without_usage,
        )

    @staticmethod
    def _or_input_rate(rate: float | None, price: ModelPricing) -> float:
        return price.input_per_million if rate is None else rate

    def _price_of(self, call: LLMCall) -> ModelPricing | None:
        return self.price_for(call.requested_model) or self.price_for(call.model)

    @staticmethod
    def _model_name(call: LLMCall) -> str:
        return call.requested_model or call.model or "unknown"
