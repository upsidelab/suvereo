import logging
from abc import ABC, ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Type

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from ..injectors import BaseInjector
from ..utils import RequiredFieldsModel, validate_required_vars

if TYPE_CHECKING:
    from ..builder import BaseAgentBuilder
    from ..config import AgentConfig

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
        "TOOLS": list[BaseModel],
    }


class ExtraArgsClassBase(metaclass=AgentExtraArgsClassBaseMeta):
    __abstract__ = True


class BaseAgent(ABC, ExtraArgsClassBase):
    """Base class of every agent.

    Subclasses implement ``get_answer`` and declare these class variables:

    - ``NAME``: the name shown in the UI.
    - ``AGENT_KEY``: unique identifier of the agent class. Agentic execution definitions refer to it.
    - ``AGENT_ARGS``: a ``RequiredFieldsModel`` of per-agent settings, meant for what changes how the agent
      behaves. Its fields become a form section in the UI and the values are stored per agent.
    - ``PROMPT_INPUT``: a ``RequiredFieldsModel`` of per-agent settings, used as variables of the system prompt:
      each field is available in the prompt as ``{field_name}``. Stored like ``AGENT_ARGS``.
    - ``TOOLS``: the tool configs of the agent. The settings of each tool (``CONFIGURATION_ARGS``) are stored
      per agent as well.
    - ``FILE_UPLOAD``: whether agents of this type accept uploaded files.
    - ``SYSTEM_PROMPT``: the system prompt template; the fields of ``PROMPT_INPUT`` fill its variables.
    - ``BUILDER_CLASS``: the builder that assembles the agent. ``None`` selects the framework's default builder;
      declare one when the agent needs a vertical's builder (e.g. one wiring domain-specific retrievers).

    An agentic execution that needs another prompt or extra tools declares them on its definition.

    The framework only stores the values of ``AGENT_ARGS`` and ``PROMPT_INPUT``. When the agent is built they
    replace the class variables with instances of the models, so ``self.AGENT_ARGS.<field>`` and
    ``self.PROMPT_INPUT.<field>`` hold the saved values. The agent decides how to use ``AGENT_ARGS``. Override
    ``_get_system_prompt_variables`` to change which variables the system prompt receives.
    """

    NAME = None
    AGENT_KEY = None
    AGENT_ARGS = None
    PROMPT_INPUT = None
    TOOLS = []

    FILE_UPLOAD = False
    SYSTEM_PROMPT: Optional[str] = None
    BUILDER_CLASS: Optional[Type["BaseAgentBuilder"]] = None

    def __init__(
        self,
        tools: list[BaseTool],
        llm: BaseLanguageModel,
        system_prompt: str,
        conversation_id: Any,
        injector: BaseInjector,
        conversation_history_token_limit: int,
        callback_handler: BaseCallbackHandler | None = None,
    ):
        self._tools = tools
        self._llm = llm
        self._system_prompt = system_prompt
        self._conversation_id = conversation_id
        self._callback_handler = callback_handler
        self._injector = injector
        self._conversation_history_token_limit = conversation_history_token_limit
        self._dynamic_tools: list[BaseTool] = []

    @classmethod
    def get_config(cls) -> "AgentConfig":
        """Return the agent's configuration.

        Returns an ``AgentConfigWithDefaults``: fields left unset are filled from the host's defaults.
        """
        from ..config import AgentConfigWithDefaults

        return AgentConfigWithDefaults(system_prompt=cls.SYSTEM_PROMPT, tools=cls.TOOLS)

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

    @abstractmethod
    async def aget_answer(self, input_text: str) -> str:
        pass

    def _get_system_prompt(self) -> str:
        return self._system_prompt.format(**self._get_system_prompt_variables())

    def _get_system_prompt_variables(self) -> dict:
        """Return variables to format into the system prompt template.

        By default these are the fields of ``PROMPT_INPUT``, available in the prompt as ``{field_name}``.
        Override to rename them or to compute others, and call ``super()`` to keep the defaults.
        """
        if isinstance(self.PROMPT_INPUT, BaseModel):
            return self.PROMPT_INPUT.model_dump()
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
