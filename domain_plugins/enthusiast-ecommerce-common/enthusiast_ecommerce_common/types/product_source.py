from enthusiast_common.integrations import BaseSourceIntegrationType


class ProductSourceType(BaseSourceIntegrationType):
    """Marker for integrations that fetch products from an external source.

    Concrete implementations (e.g. ``ProductSyncManager`` in the vertical) must
    implement ``sync(plugin, dataset_id)``.
    """
