from pydantic import Field

from .base import EvalModel


class ModelPricing(EvalModel):
    """USD per million tokens, overriding the pricing table for one model."""

    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    cached_input_per_million: float | None = Field(default=None, ge=0)
    cache_write_5m_input_per_million: float | None = Field(default=None, ge=0)
    cache_write_1h_input_per_million: float | None = Field(default=None, ge=0)
