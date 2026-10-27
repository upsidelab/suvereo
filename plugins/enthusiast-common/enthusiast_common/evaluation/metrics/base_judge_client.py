from ..base_model_client import BaseModelClient


class BaseJudgeClient(BaseModelClient):
    """The model LLM-based metrics ask; the host implements it with the suite's judge model and tracks its cost."""
