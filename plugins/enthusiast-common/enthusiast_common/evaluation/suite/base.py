from pydantic import BaseModel, ConfigDict


class EvalModel(BaseModel):
    """Base for suite models; unknown keys are errors, so a typo in a suite fails validation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
