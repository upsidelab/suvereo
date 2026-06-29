from django.apps import AppConfig


class EcommerceVerticalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ecommerce_vertical"
    verbose_name = "Ecommerce Vertical"

    def ready(self):
        from catalog.integration_type_registry import IntegrationTypeRegistry
        from ecommerce_vertical.sync import DocumentSyncManager, ProductSyncManager

        IntegrationTypeRegistry().register(ProductSyncManager)
        IntegrationTypeRegistry().register(DocumentSyncManager)
