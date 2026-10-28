from typing import Any, Iterable, TypeVar

from suvereo_common.retrievers import BaseSimilaritySearcher
from pgvector.django import CosineDistance

T = TypeVar("T")


class EmbeddingSimilaritySearcher(BaseSimilaritySearcher):
    """Ranks chunks by pgvector cosine distance to the query embedding."""

    def search(
        self,
        chunk_model: type[T],
        dataset_filter: str,
        data_set_id: Any,
        embedding_vector: list[float],
        max_objects: int,
    ) -> Iterable[T]:
        embedding_distance = CosineDistance("embedding", embedding_vector)
        return chunk_model.objects.filter(**{dataset_filter: data_set_id}).order_by(embedding_distance)[
            :max_objects
        ]
