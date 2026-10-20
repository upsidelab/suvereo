from pydantic import Field

from .base import EvalModel
from .model_pricing import ModelPricing


class ModelTarget(EvalModel):
    """A model to run the agent, or the judge, with."""

    provider: str = Field(description="A language model provider's NAME, e.g. OpenAI.")
    model: str
    label: str | None = Field(default=None, description="Shown in reports instead of the model name.")
    pricing: ModelPricing | None = None

    @property
    def display_label(self) -> str:
        return self.label or self.model
