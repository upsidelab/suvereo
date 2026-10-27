from enthusiast_common.evaluation.base_model_client import BaseModelClient
from enthusiast_common.evaluation.suite import ModelTarget


class ScriptedJudge(BaseModelClient):
    """Replies with prepared answers in turn, the last one repeating, and keeps the prompts and models it was sent."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.models: list[ModelTarget | None] = []

    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        self.prompts.append(prompt)
        self.models.append(model)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
