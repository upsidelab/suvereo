from pydantic import Field

from .base import EvalModel


class ModelPricing(EvalModel):
    """USD per million tokens, overriding the pricing table for one model."""

    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    cached_input_per_million: float | None = Field(default=None, ge=0)
    #: Writing input to the prompt cache (Anthropic bills it above the input rate); defaults to the input rate.
    cache_write_input_per_million: float | None = Field(default=None, ge=0)
