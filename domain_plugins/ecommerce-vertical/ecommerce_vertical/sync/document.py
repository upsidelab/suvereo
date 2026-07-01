from enthusiast_ecommerce_common import DocumentSourcePlugin
from enthusiast_ecommerce_common.interfaces.integration_managers import BaseDocumentSourceManager

from ecommerce_vertical.models import Document


class DocumentSourceManager(BaseDocumentSourceManager):
    """Syncs documents from a DocumentSourcePlugin into the ecommerce vertical."""

    def sync(self, plugin: DocumentSourcePlugin, dataset_id: int) -> None:
        """Fetch documents via the plugin and upsert + index each one."""
        from catalog.indexing.pipeline import index_entity

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
