import logging
from abc import ABC, ABCMeta, abstractmethod
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from ..injectors import BaseInjector
from ..utils import RequiredFieldsModel, validate_required_vars

logger = logging.getLogger(__name__)


class ExtraArgsClassBaseMeta(ABCMeta):
    REQUIRED_VARS = {}

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if not namespace.get("__abstract__", False):
            return validate_required_vars(cls, name, cls.REQUIRED_VARS)
        return cls


class AgentExtraArgsClassBaseMeta(ExtraArgsClassBaseMeta):
    REQUIRED_VARS = {
        "AGENT_ARGS": RequiredFieldsModel,
        "PROMPT_INPUT": RequiredFieldsModel,
        "PROMPT_EXTENSION": RequiredFieldsModel,
        "TOOLS": list[BaseModel],
    }


class ExtraArgsClassBase(metaclass=AgentExtraArgsClassBaseMeta):
    __abstract__ = True


class BaseAgent(ABC, ExtraArgsClassBase):
    NAME = None
    AGENT_KEY = None
    AGENT_ARGS = None
    PROMPT_INPUT = None
    PROMPT_EXTENSION = None
    TOOLS = []

    FILE_UPLOAD = False

    def __init__(
        self,
        tools: list[BaseTool],
        llm: BaseLanguageModel,
        system_prompt: str,
        conversation_id: Any,
        injector: BaseInjector,
        callback_handler: BaseCallbackHandler | None = None,
    ):
        self._tools = tools
        self._llm = llm
        self._system_prompt = system_prompt
        self._conversation_id = conversation_id
        self._callback_handler = callback_handler
        self._injector = injector
        self._dynamic_tools: list[BaseTool] = []

    def set_dynamic_tools(self, tools: list[BaseTool]) -> None:
        """Attach tools fetched at build time from tool-providing integrations (e.g. MCP servers).

        A tool whose name is already taken is dropped, because nothing downstream would complain:
        a model handed two tools of the same name picks between them arbitrarily. The agent's own
        tools always win, so connecting a server can never quietly replace built-in behaviour, and
        among integrations the first one resolved keeps the name.
        """
        taken = {tool.NAME for tool in self._tools}
        kept = []
        for tool in tools:
            if tool.name in taken:
                logger.warning(
                    "Ignoring tool '%s' from a connected integration: that name is already taken",
                    tool.name,
                )
                continue
            taken.add(tool.name)
            kept.append(tool)
        self._dynamic_tools = kept

    @abstractmethod
    def get_answer(self, input_text: str) -> str:
        pass

    def _get_system_prompt_variables(self) -> dict:
        """Return variables to format into the system prompt template."""
        return {}

    def set_runtime_arguments(self, runtime_arguments: Any) -> None:
        tools_runtime_arguments = runtime_arguments.pop("tools")
        for key, value in runtime_arguments.items():
            class_field_key = key.upper()
            field = getattr(self, class_field_key)
            if field is None:
                continue
            setattr(self, key.upper(), field(**value))
        for index, tool_runtime_args in enumerate(tools_runtime_arguments):
            self._tools[index].set_runtime_arguments(tool_runtime_args)
