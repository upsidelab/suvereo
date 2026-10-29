from openai import AzureOpenAI
from suvereo_common.registry.embeddings import EmbeddingProvider
from suvereo_common.utils import prioritize_items

PRIORITIZED_MODELS = ["text-embedding-3-large", "text-embedding-3-small"]


class AzureOpenAIEmbeddingProvider(EmbeddingProvider):
    NAME = "Azure OpenAI"

    def generate_embeddings(self, content: str) -> list[float]:
        """
        Generates and returns an embedding vector for the given content using OpenAI's embeddings API.

        Args:
            content (str): The input text for which the embedding vector is to be generated.
        """
        openai_embedding = AzureOpenAI().embeddings.create(
            model=self._model, dimensions=self._dimensions, input=content
        )

        return openai_embedding.data[0].embedding

    @staticmethod
    def available_models() -> list[str]:
        all_models = AzureOpenAI().models.list().data
        embedding_models = [model.id for model in all_models if model.id.startswith("text-embedding")]
        return prioritize_items(embedding_models, PRIORITIZED_MODELS)
