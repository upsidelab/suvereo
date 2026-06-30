
from enthusiast_common.integrations import BaseSourceIntegrationType
from enthusiast_ecommerce_common.interfaces.ecommerce_integration import ECommerceIntegrationPlugin
from enthusiast_ecommerce_common.types import ECommerceIntegrationType


class ECommerceIntegrationSyncManager(BaseSourceIntegrationType):
    """Syncs products from an ECommerceIntegrationPlugin by delegating to its product source."""

    HANDLES_TYPE = ECommerceIntegrationType

    def sync(self, plugin: ECommerceIntegrationPlugin, dataset_id: int) -> None:
        from ecommerce_vertical.sync.product import ProductSyncManager

        source = plugin.build_product_source()
        ProductSyncManager().sync(source, dataset_id)
