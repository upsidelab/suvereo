from typing import NotRequired, TypedDict

from suvereo_common.oauth import OAuthPendingAuthorization


class PendingFlow(TypedDict):
    integration_type: str
    data_set_id: int
    pending: OAuthPendingAuthorization
    origin: str
    user_id: int
    client_key: list[str]


class HandshakeOutcome(TypedDict):
    config: NotRequired[dict[str, str]]
    error: NotRequired[str]


class FlowResult(HandshakeOutcome):
    user_id: int
    data_set_id: int
