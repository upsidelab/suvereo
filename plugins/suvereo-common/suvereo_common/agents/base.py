import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Type

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from ..injectors import BaseInjector
from ..utils import RequiredFieldsModel
from .meta import AgentExtraArgsClassBaseMeta

if TYPE_CHECKING:
    from ..builder import BaseAgentBuilder
    from ..config import AgentConfig, ToolConfig

logger = logging.getLogger(__name__)


class BaseAgent(ABC, metaclass=AgentExtraArgsClassBaseMeta):
    """Base class of every agent.

    Subclasses implement ``get_answer`` and declare these class variables:

    - ``NAME``: the name shown in the UI.
    - ``AGENT_KEY``: unique identifier of the agent class. Agentic execution definitions refer to it.
    - ``AGENT_ARGS``: a ``RequiredFieldsModel`` of per-agent settings, meant for what changes how the agent
      behaves. Its fields become a form section in the UI and the values are stored per agent.
    - ``PROMPT_INPUT``: a ``RequiredFieldsModel`` of per-agent settings, used as variables of the system prompt:
      each field is available in the prompt as ``{field_name}``. Stored like ``AGENT_ARGS``.
    - ``TOOLS``: the tool configs of the agent. The settings of each tool (``CONFIGURATION_ARGS``) are stored
      per agent as well, keyed by the tool's ``NAME``.
    - ``FILE_UPLOAD``: whether agents of this type accept uploaded files.
    - ``SYSTEM_PROMPT``: the system prompt template; the fields of ``PROMPT_INPUT`` fill its variables.
      Required, like ``NAME`` and ``AGENT_KEY``: a concrete agent class that leaves any of them
      undefined or empty fails at import time.
    - ``CONVERSATION_HISTORY_TOKEN_LIMIT``: how many tokens of conversation history the agent sends to the model.
      ``None`` keeps the host's default.
    - ``MEMORY_COMPACTOR_ENABLED``: whether the agent summarises old messages to stay within the history limit.
    - ``BUILDER_CLASS``: the builder that assembles the agent. ``None`` selects the framework's default builder;
      declare one when the agent needs a vertical's builder (e.g. one wiring domain-specific retrievers).

    An agentic execution that needs another prompt or extra tools declares them on its definition.

    The framework only stores the values of ``AGENT_ARGS`` and ``PROMPT_INPUT``. When the agent is built they
    replace the class variables with instances of the models, so ``self.AGENT_ARGS.<field>`` and
    ``self.PROMPT_INPUT.<field>`` hold the saved values. The agent decides how to use ``AGENT_ARGS``. Override
    ``_get_system_prompt_variables`` to change which variables the system prompt receives.
    """

    NAME: str
    AGENT_KEY: str
    AGENT_ARGS: Optional[Type[RequiredFieldsModel] | RequiredFieldsModel] = None
    PROMPT_INPUT: Optional[Type[RequiredFieldsModel] | RequiredFieldsModel] = None
    TOOLS: list["ToolConfig"] = []

    FILE_UPLOAD: bool = False
    SYSTEM_PROMPT: str
    CONVERSATION_HISTORY_TOKEN_LIMIT: Optional[int] = None
    MEMORY_COMPACTOR_ENABLED: bool = False
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

        return AgentConfigWithDefaults(
            system_prompt=cls.SYSTEM_PROMPT,
            tools=cls.TOOLS,
            conversation_history_token_limit=cls.CONVERSATION_HISTORY_TOKEN_LIMIT,
            memory_compactor_enabled=cls.MEMORY_COMPACTOR_ENABLED,
        )

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
        tools_runtime_arguments = runtime_arguments.pop("tools", {})
        if not isinstance(tools_runtime_arguments, dict):
            logger.warning("Tool settings are stored as a list; tools use their defaults until the agent is saved")
            tools_runtime_arguments = {}
        for key, value in runtime_arguments.items():
            class_field_key = key.upper()
            field = getattr(self, class_field_key)
            if field is None:
                continue
            setattr(self, key.upper(), field(**value))
        for tool in self._tools:
            try:
                tool.set_runtime_arguments(tools_runtime_arguments.get(tool.NAME, {}))
            except ValidationError as e:
                raise ValueError(
                    f"Tool '{tool.NAME}' has missing or invalid settings; save the agent's configuration."
                ) from e
