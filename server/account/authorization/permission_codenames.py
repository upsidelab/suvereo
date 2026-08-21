from enum import StrEnum


class DatasetPermission(StrEnum):
    VIEW = "catalog.view_dataset"
    ADD = "catalog.add_dataset"
    CHANGE = "catalog.change_dataset"
    DELETE = "catalog.delete_dataset"


class AgentPermission(StrEnum):
    VIEW = "agent.view_agent"
    ADD = "agent.add_agent"
    CHANGE = "agent.change_agent"
    DELETE = "agent.delete_agent"


class IntegrationPermission(StrEnum):
    VIEW = "catalog.view_integration"
    ADD = "catalog.add_integration"
    CHANGE = "catalog.change_integration"
    DELETE = "catalog.delete_integration"
    SYNC = "catalog.sync_integration"


class ConversationPermission(StrEnum):
    CONVERSE = "agent.converse"
    VIEW_ALL = "agent.view_conversation"


class AgenticExecutionPermission(StrEnum):
    CREATE = "agent.add_agenticexecution"
    VIEW_ALL = "agent.view_agenticexecution"


class UserPermission(StrEnum):
    VIEW = "account.view_user"
    ADD = "account.add_user"
    CHANGE = "account.change_user"


class ServiceAccountPermission(StrEnum):
    VIEW = "account.view_serviceaccount"
    ADD = "account.add_serviceaccount"
    CHANGE = "account.change_serviceaccount"


class GlobalRolePermission(StrEnum):
    """Django's `auth.Group` is a global role to an API consumer, and the public codes say so."""

    VIEW = "auth.view_group"
    ASSIGN = "account.assign_group"


class DatasetRolePermission(StrEnum):
    VIEW = "account.view_datasetrole"
    ASSIGN = "account.assign_datasetrole"


class PERMISSIONS:
    DATASET = DatasetPermission
    AGENT = AgentPermission
    INTEGRATION = IntegrationPermission
    CONVERSATION = ConversationPermission
    AGENTIC_EXECUTION = AgenticExecutionPermission
    USER = UserPermission
    SERVICE_ACCOUNT = ServiceAccountPermission
    GLOBAL_ROLE = GlobalRolePermission
    DATASET_ROLE = DatasetRolePermission
