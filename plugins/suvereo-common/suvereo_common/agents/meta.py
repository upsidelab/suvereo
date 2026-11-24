from pydantic import BaseModel
from suvereo_common.utils import ExtraArgsClassBaseMeta, RequiredFieldsModel


class AgentExtraArgsClassBaseMeta(ExtraArgsClassBaseMeta):
    """Checks an agent class's extra arguments when it is defined."""

    REQUIRED_VARS = {
        "NAME": str,
        "AGENT_KEY": str,
        "SYSTEM_PROMPT": str,
    }
    OPTIONAL_VARS = {
        "AGENT_ARGS": RequiredFieldsModel,
        "PROMPT_INPUT": RequiredFieldsModel,
        "TOOLS": list[BaseModel],
    }
