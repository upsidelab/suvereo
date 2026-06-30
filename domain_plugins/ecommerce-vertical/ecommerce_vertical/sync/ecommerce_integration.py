from enthusiast_ecommerce_common.interfaces import ECommerceIntegrationPlugin
from enthusiast_ecommerce_common.interfaces.integration_managers import BaseECommerceIntegrationManager

from ecommerce_vertical.sync.product import ProductSourceManager

class ECommerceIntegrationManager(BaseECommerceIntegrationManager):
    """Syncs products from an ECommerceIntegrationPlugin by delegating to its product source."""

    def sync(self, plugin: ECommerceIntegrationPlugin, dataset_id: int) -> None:
        source = plugin.build_product_source()
        ProductSourceManager().sync(source, dataset_id)
