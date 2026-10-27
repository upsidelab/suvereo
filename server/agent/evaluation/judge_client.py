from enthusiast_common.evaluation.metrics import BaseJudgeClient
from enthusiast_common.evaluation.suite import ModelTarget

from agent.evaluation.model_client import EvalModelClient


class EvalJudgeClient(EvalModelClient, BaseJudgeClient):
    """Sends LLM metrics' judge prompts to the suite's judge, or to the model a metric names; judge cost stays apart
    from the agent's."""

    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        """Ask the metric's judge model, or else the suite's; raises ValueError when neither is set."""
        if (model or self.target) is None:
            raise ValueError("No judge model: set 'judge' in the suite or in the metric's params.")
        return super().complete(prompt, model)
