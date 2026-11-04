from unittest.mock import MagicMock

from catalog.indexing.pipeline import EmbeddingIndexer
from catalog.models import DataSet


class TestEmbeddingIndexer:
    def test_the_provider_is_built_from_the_data_set_without_looking_it_up(self):
        registry = MagicMock()
        data_set = DataSet(
            pk=7,
            is_temporary=True,
            embedding_provider="OpenAI",
            embedding_model="text-embedding-3-small",
            embedding_vector_dimensions=512,
        )

        provider = EmbeddingIndexer(registry)._provider(data_set)

        registry.provider_class_by_name.assert_called_once_with("OpenAI")
        registry.provider_class_by_name.return_value.assert_called_once_with("text-embedding-3-small", 512)
        assert provider is registry.provider_class_by_name.return_value.return_value
        registry.provider_instance_for_dataset.assert_not_called()
