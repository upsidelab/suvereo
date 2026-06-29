import json
from typing import Any

from pgvector.django import CosineDistance

from ecommerce_vertical.models import Product, ProductContentChunk


class ProductRetriever:
    """Retrieves products from the vertical's ProductContentChunk table using vector similarity."""

    def __init__(self, data_set_id: Any, max_results: int = 12):
        self.data_set_id = data_set_id
        self.max_results = max_results

    def _embed_query(self, query: str) -> list[float]:
        from django.apps import apps

        from agent.core.registries.embeddings import EmbeddingProviderRegistry

        DataSet = apps.get_model("catalog", "DataSet")
        data_set = DataSet.objects.get(pk=self.data_set_id)
        provider_class = EmbeddingProviderRegistry().provider_for_dataset(self.data_set_id)
        provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
        return provider.generate_embeddings(query)

    def find_products_matching_query(self, query: str) -> list:
        """Return ProductContentChunk instances closest to *query* in the dataset."""
        embedding = self._embed_query(query)
        return list(
            ProductContentChunk.objects.filter(product__dataset_id=self.data_set_id)
            .order_by(CosineDistance("embedding", embedding))[: self.max_results]
        )

    def product_details_as_json(self, chunks: list) -> list[dict]:
        """Deduplicate chunks by product and return a list of product dicts."""
        seen: set = set()
        result = []
        for chunk in chunks:
            product = chunk.product
            if product.id not in seen:
                seen.add(product.id)
                result.append(
                    {
                        "entry_id": product.entry_id,
                        "name": product.name,
                        "sku": product.sku,
                        "description": product.description,
                        "properties": product.properties,
                        "categories": product.categories,
                        "price": product.price,
                    }
                )
        return result

    def get_sample_products_json(self, max_results: int = 10) -> str:
        """Return a JSON string of the first *max_results* products in the dataset."""
        products = Product.objects.filter(dataset_id=self.data_set_id)[:max_results]
        result = [
            {
                "entry_id": p.entry_id,
                "name": p.name,
                "sku": p.sku,
                "description": p.description,
                "properties": p.properties,
                "categories": p.categories,
                "price": p.price,
            }
            for p in products
        ]
        return json.dumps(result)
