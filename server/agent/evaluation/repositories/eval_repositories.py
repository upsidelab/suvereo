from suvereo_common.config import RepositoriesConfig

from agent.core.repositories import (
    DjangoAgentRepository,
    DjangoConversationRepository,
    DjangoDataSetRepository,
    DjangoMessageRepository,
    DjangoUserRepository,
)

from .all_objects_repository_mixin import AllObjectsRepositoryMixin


class EvalConversationRepository(AllObjectsRepositoryMixin, DjangoConversationRepository):
    pass


class EvalDataSetRepository(AllObjectsRepositoryMixin, DjangoDataSetRepository):
    pass


class EvalAgentRepository(AllObjectsRepositoryMixin, DjangoAgentRepository):
    pass


EVAL_REPOSITORIES = RepositoriesConfig(
    user=DjangoUserRepository,
    message=DjangoMessageRepository,
    conversation=EvalConversationRepository,
    data_set=EvalDataSetRepository,
    agent=EvalAgentRepository,
)
