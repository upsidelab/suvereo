from enthusiast_common.integrations import BaseSourceIntegrationType


class DocumentSourceType(BaseSourceIntegrationType):
    """Marker for integrations that fetch documents from an external source.

    Concrete implementations (e.g. ``DocumentSyncManager`` in the vertical) must
    implement ``sync(plugin, dataset_id)``.
    """
