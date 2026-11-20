import re

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI
from pydantic import BaseModel
from suvereo_common.registry.llm import LanguageModelProvider
from suvereo_common.structures import BaseContent, LLMFile
from suvereo_common.utils import prioritize_items

PRIORITIZED_MODELS = ["gpt-4.1", "gpt-4.1-mini", "gpt-5", "gpt-5.2"]

# Model families that can't hold a text conversation with tools: they serve other endpoints
# (transcription, speech, realtime/live voice, images), need audio, or reject function tools (search).
# Each pattern matches whole dash-separated parts of the model name, e.g. "tts" in "gpt-4o-mini-tts".
UNSUPPORTED_MODEL_PATTERNS = ["transcribe", "tts", "realtime", "live", "audio", "image", "search"]
UNSUPPORTED_MODEL_REGEX = re.compile(rf"(^|-)({'|'.join(map(re.escape, UNSUPPORTED_MODEL_PATTERNS))})(-|$)")


class AzureOpenAIImageUrl(BaseModel):
    url: str


class AzureOpenAIImageContent(BaseContent):
    image_url: AzureOpenAIImageUrl


class AzureOpenAIFileObject(BaseModel):
    filename: str
    file_data: str


class AzureOpenAIFileContent(BaseContent):
    file: AzureOpenAIFileObject


class AzureOpenAILanguageModelProvider(LanguageModelProvider):
    NAME = "Azure OpenAI"

    def provide_language_model(self, callbacks: list[BaseCallbackHandler] | None = None) -> BaseLanguageModel:
        return AzureChatOpenAI(model=self._model, callbacks=callbacks, use_responses_api=True)

    def provide_streaming_language_model(self, callbacks: list[BaseCallbackHandler] | None = None, **kwargs) -> BaseLanguageModel:
        return AzureChatOpenAI(model=self._model, callbacks=callbacks, streaming=True, use_responses_api=True)

    def model_name(self) -> str:
        return self._model

    @staticmethod
    def available_models() -> list[str]:
        all_models = AzureOpenAI().models.list().data
        gpt_models = [model.id for model in all_models if model.id.startswith("gpt-")]
        chat_models = [model for model in gpt_models if not UNSUPPORTED_MODEL_REGEX.search(model)]
        return prioritize_items(chat_models, PRIORITIZED_MODELS)

    @staticmethod
    def prepare_image_object(file_object: LLMFile) -> AzureOpenAIImageContent:
        url = f"data:{file_object.content_type};base64,{file_object.content}"
        return AzureOpenAIImageContent(type="image_url", image_url=AzureOpenAIImageUrl(url=url))

    @staticmethod
    def prepare_file_object(file_object: LLMFile) -> AzureOpenAIFileContent:
        file_data = f"data:application/pdf;base64,{file_object.content}"
        return AzureOpenAIFileContent(
            type="file", file=AzureOpenAIFileObject(file_data=file_data, filename=file_object.filename)
        )
