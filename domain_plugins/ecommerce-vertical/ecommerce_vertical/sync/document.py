from typing import Any

from enthusiast_ecommerce_common.types import DocumentSourceType


class DocumentSyncManager(DocumentSourceType):
    """Syncs documents from a DocumentSourcePlugin into the ecommerce vertical."""

    HANDLES_TYPE = DocumentSourceType

    def sync(self, plugin: Any, dataset_id: Any) -> None:
        """Fetch documents via the plugin and upsert + index each one."""
        from catalog.indexing.pipeline import index_entity
        from ecommerce_vertical.models import Document

        for details in plugin.fetch():
            document, _ = Document.objects.update_or_create(
                dataset_id=dataset_id,
                url=details.url,
                defaults={
                    "title": details.title,
                    "content": details.content,
                },
            )
            index_entity(document)
