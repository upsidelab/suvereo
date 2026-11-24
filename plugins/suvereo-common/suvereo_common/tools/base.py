import inspect
from abc import ABC, ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any

from suvereo_common.registry import BaseLanguageModelRegistry

if TYPE_CHECKING:
    from suvereo_common.agents import BaseAgent

from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool as LCBaseTool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from suvereo_common.injectors import BaseInjector
from suvereo_common.utils import RequiredFieldsModel, validate_required_vars


class ToolMeta(ABCMeta):
    """Checks that a tool class declares the required class variables."""

    REQUIRED_VARS = {
        "NAME": str,
        "DESCRIPTION": str,
        "ARGS_SCHEMA": type,
        "RETURN_DIRECT": bool,
        "CONFIGURATION_ARGS": RequiredFieldsModel,
    }

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> type:
        """Create the tool class after checking its class variables."""
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if inspect.isabstract(cls):
            return cls
        return validate_required_vars(cls, name, cls.REQUIRED_VARS)


class BaseTool(metaclass=ToolMeta):
    """Base class for tools an agent can call."""

    NAME: str
    DESCRIPTION: str
    ARGS_SCHEMA: type[BaseModel]
    RETURN_DIRECT: bool
    CONFIGURATION_ARGS = None

    REQUIRED_CLASS_VARS = {
        "NAME": str,
        "DESCRIPTION": str,
        "ARGS_SCHEMA": type,
        "RETURN_DIRECT": bool,
        "CONFIGURATION_ARGS": RequiredFieldsModel,
    }

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the tool with the arguments the model chose."""

    def as_tool(self) -> LCBaseTool:
        """Return the tool as a LangChain tool."""
        return StructuredTool.from_function(
            func=self.run,
            name=self.NAME,
            description=self.DESCRIPTION,
            args_schema=self.ARGS_SCHEMA,
            return_direct=self.RETURN_DIRECT,
        )

    def set_runtime_arguments(self, runtime_arguments: Any) -> None:
        """Apply the tool settings stored on the agent."""
        field = getattr(self, "CONFIGURATION_ARGS", None)
        if field is None:
            return
        self.CONFIGURATION_ARGS = field(**runtime_arguments)


class BaseFunctionTool(BaseTool, ABC):
    """A tool that needs no language model or injector."""


class BaseLLMTool(BaseTool, ABC):
    """A tool that uses the language model and the injector."""

    def __init__(
        self,
        data_set_id: Any,
        llm: BaseLanguageModel,
        injector: BaseInjector,
    ):
        self._data_set_id = data_set_id
        self._llm = llm
        self._injector = injector


class BaseFileTool(BaseTool, ABC):
    """A tool that works with files attached to the conversation."""

    def __init__(
        self,
        data_set_id: Any,
        conversation_id: Any,
        llm: BaseLanguageModel,
        injector: BaseInjector,
        llm_registry: BaseLanguageModelRegistry,
    ):
        self._data_set_id = data_set_id
        self._conversation_id = conversation_id
        self._llm = llm
        self._injector = injector
        self._llm_registry = llm_registry


class BaseAgentTool(BaseTool, ABC):
    """A tool that calls another agent."""

    def __init__(
        self,
        agent: "BaseAgent",  # noqa: F821
    ):
        self._agent = agent
