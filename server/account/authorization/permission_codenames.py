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
    VIEW = "account.view_user"


class ServiceAccountPermission(StrEnum):
    ADD = "account.add_serviceaccount"
    CHANGE = "account.change_serviceaccount"
    VIEW = "account.view_serviceaccount"


class GroupPermission(StrEnum):
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
    GROUP = GroupPermission
    DATASET_ROLE = DatasetRolePermission

PERMISSION_ENTITIES: dict[str, type[StrEnum]] = {
    name: permission_set
    for name, permission_set in vars(PERMISSIONS).items()
    if isinstance(permission_set, type) and issubclass(permission_set, StrEnum)
}

# The public permissions vocabulary, derived rather than maintained from PERMISSIONS
PUBLIC_CODES: dict[str, str] = {
    str(member): f"{entity_name.lower()}.{member.name.lower()}"
    for entity_name, permission_set in PERMISSION_ENTITIES.items()
    for member in permission_set
}

INTERNAL_CODES: dict[str, str] = {public: internal for internal, public in PUBLIC_CODES.items()}


def entity_label(entity_name: str) -> str:
    """The display name for a permission entity - "AGENTIC_EXECUTION" reads as "Agentic execution"."""
    return entity_name.replace("_", " ").capitalize()


# What each kind of grant may carry, which is what `scope` selects on the permission endpoint.
# A DatasetRole is limited to the dual-scope codenames: a global-only one sitting in a role is
# never read by anything, so accepting it would misreport what the role does. A Group may carry
# those *and* the global-only ones - granting a dual-scope codename globally is meaningful, it
# just means "on every data set". Between them the two lists cover every codename declared above:
# everything this application names is grantable somewhere, and everything it does not consult is
# left undeclared.
_GLOBAL_ONLY_PERMISSIONS: list[str] = [
    *DatasetPermission,
    *UserPermission,
    *ServiceAccountPermission,
    *GroupPermission,
    DatasetRolePermission.VIEW,
]

DATASET_SCOPE_PERMISSIONS: list[str] = [
    *AgentPermission,
    *IntegrationPermission,
    *ConversationPermission,
    *AgenticExecutionPermission,
    DatasetRolePermission.ASSIGN,
]

GLOBAL_SCOPE_PERMISSIONS: list[str] = [*_GLOBAL_ONLY_PERMISSIONS, *DATASET_SCOPE_PERMISSIONS]

PERMISSION_SCOPES: dict[str, list[str]] = {
    "global": GLOBAL_SCOPE_PERMISSIONS,
    "dataset": DATASET_SCOPE_PERMISSIONS,
}

# Granting a codename on the left requires also granting the one on the right. Derived from the
# member names rather than spelled out, because the naming *is* the rule: add/change/delete of an
# entity requires its view. Everything else falls outside by construction - Conversation and
# Agentic Execution have no VIEW member (their oversight codename is VIEW_ALL, not a prerequisite
# for CONVERSE/CREATE), and SYNC/ASSIGN are none of the three.
VIEW_DEPENDENCIES: dict[str, str] = {
    permission_set[member_name]: permission_set["VIEW"]
    for permission_set in PERMISSION_ENTITIES.values()
    if "VIEW" in permission_set.__members__
    for member_name in ("ADD", "CHANGE", "DELETE")
    if member_name in permission_set.__members__
}


def permission_label(permission) -> str:
    """The `app_label.codename` form of a `Permission` row, matching what `has_perm` expects."""
    return f"{permission.content_type.app_label}.{permission.codename}"
