from pydantic import BaseModel, ConfigDict


class NoParams(BaseModel):
    """The PARAMS of a metric that takes none; any key given is an error."""

    model_config = ConfigDict(extra="forbid")
