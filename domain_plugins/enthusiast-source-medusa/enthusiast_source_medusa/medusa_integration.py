from typing import Optional

from enthusiast_common.utils import RequiredFieldsModel
from enthusiast_ecommerce_common.connectors import ECommercePlatformConnector
from enthusiast_ecommerce_common.interfaces import ECommerceIntegrationPlugin, ProductSourcePlugin
from pydantic import Field

from .medusa_platform_connector import MedusaPlatformConnector
from .medusa_product_source import MedusaProductSource


class MedusaIntegrationConfig(RequiredFieldsModel):
    base_url: str = Field(title="Base URL", description="Medusa API URL")
    api_key: str = Field(title="API key", description="Medusa API Key")
    admin_base_url: Optional[str] = Field(title="Admin base URL", description="(Optional) Medusa Admin URL, if different than the API URL", default=None)


class MedusaIntegration(ECommerceIntegrationPlugin):
    TYPE = "medusa"
    LABEL = "Medusa"
    CONFIGURATION_ARGS = MedusaIntegrationConfig

    def build_connector(self) -> ECommercePlatformConnector:
        return MedusaPlatformConnector(
            base_url=self.CONFIGURATION_ARGS.base_url,
            api_key=self.CONFIGURATION_ARGS.api_key,
            admin_base_url=self.CONFIGURATION_ARGS.admin_base_url or self.CONFIGURATION_ARGS.base_url,
        )

    def build_product_source(self) -> ProductSourcePlugin:
        source = MedusaProductSource()
        source.set_runtime_arguments({"configuration_args": {
            "base_url": self.CONFIGURATION_ARGS.base_url,
            "api_key": self.CONFIGURATION_ARGS.api_key,
        }})
        return source
