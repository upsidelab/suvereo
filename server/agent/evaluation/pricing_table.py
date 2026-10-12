import re
from pathlib import Path

import yaml
from enthusiast_common.evaluation.suite import ModelPricing
from enthusiast_common.evaluation.trace import ExecutionTrace, LLMCall
from pydantic import BaseModel

DEFAULT_TABLE = Path(__file__).with_name("pricing.yaml")
PER_TOKEN = 1_000_000
DATED_SNAPSHOT = re.compile(r"-(\d{4}-\d{2}-\d{2}|\d{8})$")


class TraceCost(BaseModel):
    """What a trace's LLM calls cost; None when any call's model has no price."""

    usd: float | None
    unpriced_models: list[str] = []


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
        price = self.price_for(call.requested_model) or self.price_for(call.model)
        if price is None:
            return None
        cached = min(call.cached_input_tokens, call.input_tokens)
        cached_rate = (
            price.cached_input_per_million if price.cached_input_per_million is not None else price.input_per_million
        )
        return (
            (call.input_tokens - cached) * price.input_per_million
            + cached * cached_rate
            + call.output_tokens * price.output_per_million
        ) / PER_TOKEN

    def trace_cost(self, trace: ExecutionTrace) -> TraceCost:
        """The trace's total cost, or None with the unpriced model names if any call cannot be priced."""
        costs = [(call, self.call_cost(call)) for call in trace.llm_calls]
        unpriced = sorted({call.requested_model or call.model or "unknown" for call, cost in costs if cost is None})
        return TraceCost(usd=None if unpriced else sum(cost for _, cost in costs), unpriced_models=unpriced)
