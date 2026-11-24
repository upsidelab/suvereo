import json

from suvereo_common.agentic_execution.input import ExecutionInputType
from suvereo_common.agentic_execution.memory import ToolScratchpad
from suvereo_common.agentic_execution.validators.base import BaseExecutionValidator
from suvereo_common.agentic_execution.validators.failure_response import ValidatorFailureResponse
from suvereo_common.agentic_execution.validators.response import ValidatorResponse
from suvereo_common.agentic_execution.validators.success_response import ValidatorSuccessResponse


class IsValidJsonValidator(BaseExecutionValidator):
    """Validates that the LLM response is parseable as JSON."""

    FEEDBACK_MESSAGE = (
        "The response is not valid JSON. "
        "Please return the same data as a valid JSON object."
    )

    def validate(self,
                 response: str,
                 _execution_input: ExecutionInputType,
                 _tool_scratchpad: ToolScratchpad) -> ValidatorResponse:
        """Check that the response is valid JSON."""
        try:
            json.loads(response)
            return ValidatorSuccessResponse()
        except (json.JSONDecodeError, TypeError):
            return ValidatorFailureResponse(feedback=self.FEEDBACK_MESSAGE)
