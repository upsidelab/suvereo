from typing import Any

from pydantic import Field

from .eval_case import EvalCase


class AgenticExecutionEvalCase(EvalCase):
    """A case of an execution suite: the agent gets one structured input."""

    input: dict[str, Any] = Field(default={}, description="Validated against the execution's INPUT_TYPE.")
