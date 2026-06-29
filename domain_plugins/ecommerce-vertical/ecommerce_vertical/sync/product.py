from typing import Any

from enthusiast_ecommerce_common.types import ProductSourceType


class ProductSyncManager(ProductSourceType):
    """Syncs products from a ProductSourcePlugin into the ecommerce vertical."""

    HANDLES_TYPE = ProductSourceType

    def sync(self, plugin: Any, dataset_id: Any) -> None:
        """Fetch products via the plugin and upsert + index each one."""
        from catalog.indexing.pipeline import index_entity
        from ecommerce_vertical.models import Product

        for details in plugin.fetch():
            product, _ = Product.objects.update_or_create(
                dataset_id=dataset_id,
                entry_id=details.entry_id,
                defaults={
                    "name": details.name,
                    "slug": details.slug,
                    "sku": details.sku,
                    "description": details.description,
                    "properties": details.properties,
                    "categories": details.categories,
                    "price": details.price,
                },
            )
            index_entity(product)
