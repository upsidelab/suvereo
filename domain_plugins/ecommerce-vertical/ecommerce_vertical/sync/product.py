from typing import Any

from enthusiast_ecommerce_common import ProductSourcePlugin
from enthusiast_ecommerce_common.interfaces.integration_managers import BaseProductSourceManager

from ecommerce_vertical.models import Product


class ProductSourceManager(BaseProductSourceManager):
    """Syncs products from a ProductSourcePlugin into the ecommerce vertical."""

    def sync(self, plugin: ProductSourcePlugin, dataset_id: Any, integration_id: Any) -> None:
        """Fetch products via the plugin and upsert + index each one."""
        from catalog.indexing.pipeline import index_entity

        for details in plugin.fetch():
            product, _ = Product.objects.update_or_create(
                dataset_id=dataset_id,
                entry_id=details.entry_id,
                defaults={
                    "integration_id": integration_id,
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
