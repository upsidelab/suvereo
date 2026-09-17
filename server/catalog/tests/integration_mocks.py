from enthusiast_common.integrations import BaseIntegration
from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class MockConfigArgs(RequiredFieldsModel):
    marker: str = Field(default="")


class MockSingleInstanceIntegration(BaseIntegration):
    TYPE = "mock_single"
    NAME = "Mock Single Instance"
    INTEGRATION_TYPE_NAME = "Mock category"
    ALLOWS_MULTIPLE_INSTANCES = False


class MockMultiInstanceIntegration(BaseIntegration):
    TYPE = "mock_multi"
    NAME = "Mock Multi Instance"
    INTEGRATION_TYPE_NAME = "Mock category"
    ALLOWS_MULTIPLE_INSTANCES = True
    CONFIGURATION_ARGS = MockConfigArgs

    def instance_name(self) -> str:
        """Label by config, the way a real multi-instance plugin distinguishes its instances."""
        return f"{self.NAME} ({self.CONFIGURATION_ARGS.marker})"
