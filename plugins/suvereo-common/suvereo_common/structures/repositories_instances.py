from dataclasses import dataclass

from suvereo_common.repositories import (
    BaseAgentRepository,
    BaseConversationRepository,
    BaseDataSetRepository,
    BaseMessageRepository,
    BaseUserRepository,
)


@dataclass
class RepositoriesInstances:
    """The repositories an agent is built with."""

    user: BaseUserRepository
    message: BaseMessageRepository
    conversation: BaseConversationRepository
    data_set: BaseDataSetRepository
    agent: BaseAgentRepository
