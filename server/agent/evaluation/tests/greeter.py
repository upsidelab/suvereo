from abc import ABC, abstractmethod

from enthusiast_common.evaluation.mocks import BaseMock, BaseMockIntegration
from enthusiast_common.integrations import BaseIntegration


class Greeter(ABC):
    @abstractmethod
    def greet(self, name: str) -> str: ...


class GreeterIntegrationPlugin(BaseIntegration):
    INTEGRATION_TYPE_NAME = "Greeter"

    @abstractmethod
    def build_greeter(self) -> Greeter: ...


class OtherIntegrationPlugin(BaseIntegration):
    INTEGRATION_TYPE_NAME = "Other"


class GreeterMockIntegration(BaseMockIntegration, GreeterIntegrationPlugin):
    TYPE = "mock_greeter"
    NAME = "Mock greeter"
    MOCK_CLASS = BaseMock.declarative(Greeter)

    def build_greeter(self) -> Greeter:
        return self.mock


class RealGreeterIntegration(GreeterIntegrationPlugin):
    TYPE = "real_greeter"
    NAME = "Real greeter"

    def build_greeter(self) -> Greeter:
        raise AssertionError("a real integration must never be used here")
