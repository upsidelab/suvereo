import json
from abc import ABC, abstractmethod

from suvereo_common.agentic_execution import BaseAgenticExecutionDefinition, ExecutionInputType
from suvereo_common.evaluation.mocks import BaseMock, BaseMockIntegration
from suvereo_common.integrations import BaseIntegration

from agent.evaluation.integrations import EvalIntegrationPluginResolver


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


class IncompleteGreeterMockIntegration(BaseMockIntegration, GreeterIntegrationPlugin):
    TYPE = "mock_incomplete_greeter"
    NAME = "Mock greeter missing build_greeter"
    MOCK_CLASS = BaseMock.declarative(Greeter)


class RealGreeterIntegration(GreeterIntegrationPlugin):
    TYPE = "real_greeter"
    NAME = "Real greeter"

    def build_greeter(self) -> Greeter:
        raise AssertionError("a real integration must never be used here")


class GreetingInput(ExecutionInputType):
    name: str


class GreetingExecution(BaseAgenticExecutionDefinition):
    """Greets through whichever greeter the run resolves, without an LLM, as an agent's tool would."""

    EXECUTION_KEY = "greeting"
    AGENT_KEY = "greeter-agent"
    NAME = "Greeting"
    INPUT_TYPE = GreetingInput

    def execute(self, input_data, conversation):
        greeting = EvalIntegrationPluginResolver().resolve(None, GreeterIntegrationPlugin).build_greeter()
        reply = greeting.greet(input_data.name)
        conversation.tool_scratchpad.record("greet", reply)
        return json.dumps({"greeting": reply})
