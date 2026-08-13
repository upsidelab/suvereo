from enum import StrEnum


class DatasetPermission(StrEnum):
    ADD = "catalog.add_dataset"
    CHANGE = "catalog.change_dataset"
    DELETE = "catalog.delete_dataset"
    VIEW = "catalog.view_dataset"


class AgentPermission(StrEnum):
    ADD = "agent.add_agent"
    CHANGE = "agent.change_agent"
    DELETE = "agent.delete_agent"
    VIEW = "agent.view_agent"


class IntegrationPermission(StrEnum):
    ADD = "catalog.add_integration"
    CHANGE = "catalog.change_integration"
    DELETE = "catalog.delete_integration"
    VIEW = "catalog.view_integration"
    SYNC = "catalog.sync_integration"


class ConversationPermission(StrEnum):
    CONVERSE = "agent.converse"
    VIEW_ALL = "agent.view_conversation"


class AgenticExecutionPermission(StrEnum):
    CREATE = "agent.add_agenticexecution"
    VIEW_ALL = "agent.view_agenticexecution"


class UserPermission(StrEnum):
    ADD = "account.add_user"
    CHANGE = "account.change_user"
    DELETE = "account.delete_user"
    VIEW = "account.view_user"


class ServiceAccountPermission(StrEnum):
    ADD = "account.add_serviceaccount"
    CHANGE = "account.change_serviceaccount"
    VIEW = "account.view_serviceaccount"


class GroupPermission(StrEnum):
    ADD = "auth.add_group"
    CHANGE = "auth.change_group"
    DELETE = "auth.delete_group"
    VIEW = "auth.view_group"


class DatasetRolePermission(StrEnum):
    ADD = "account.add_datasetrole"
    CHANGE = "account.change_datasetrole"
    DELETE = "account.delete_datasetrole"
    VIEW = "account.view_datasetrole"


class PERMISSIONS:
    DATASET = DatasetPermission
    AGENT = AgentPermission
    INTEGRATION = IntegrationPermission
    CONVERSATION = ConversationPermission
    AGENTIC_EXECUTION = AgenticExecutionPermission
    USER = UserPermission
    SERVICE_ACCOUNT = ServiceAccountPermission
    GROUP = GroupPermission
    DATASET_ROLE = DatasetRolePermission
