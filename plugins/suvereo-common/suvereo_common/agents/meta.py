from pydantic import BaseModel

from ..utils import ExtraArgsClassBaseMeta, RequiredFieldsModel


class AgentExtraArgsClassBaseMeta(ExtraArgsClassBaseMeta):
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
