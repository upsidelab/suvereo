from enthusiast_common.evaluation.metrics import BaseJudgeClient


class ScriptedJudge(BaseJudgeClient):
    """Replies with prepared answers in turn, the last one repeating, and keeps the prompts it was sent."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
