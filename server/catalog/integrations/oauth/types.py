"""The shapes held in storage while a handshake is in flight."""

from typing import NotRequired, TypedDict

from enthusiast_common.oauth import OAuthPendingAuthorization


class PendingFlow(TypedDict):
    """A handshake that has begun and is waiting for the provider to send the admin back."""

    integration_type: str
    data_set_id: int
    pending: OAuthPendingAuthorization
    origin: str
    user_id: int
    client_key: list[str]


class HandshakeOutcome(TypedDict):
    """How a handshake ended: config to store, or something to tell the admin."""

    config: NotRequired[dict[str, str]]
    error: NotRequired[str]


class FlowResult(HandshakeOutcome):
    """An outcome once it is owned, so only the account that began the flow may collect it."""

    user_id: int
    data_set_id: int
