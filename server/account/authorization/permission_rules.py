from .permission_codenames import (
    AgenticExecutionPermission,
    AgentPermission,
    ConversationPermission,
    DatasetPermission,
    DatasetRolePermission,
    GroupPermission,
    IntegrationPermission,
    ServiceAccountPermission,
    UserPermission,
)

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

# What each permission requires, keyed by the requirement: granting anything in the list on the
# right means the permission on the left has to be granted too.
PERMISSION_DEPENDENCIES: dict[str, list[str]] = {
    DatasetPermission.VIEW: [
        DatasetPermission.ADD,
        DatasetPermission.CHANGE,
        DatasetPermission.DELETE,
        *DATASET_SCOPE_PERMISSIONS,
    ],
    AgentPermission.VIEW: [
        AgentPermission.ADD,
        AgentPermission.CHANGE,
        AgentPermission.DELETE,
    ],
    IntegrationPermission.VIEW: [
        IntegrationPermission.ADD,
        IntegrationPermission.CHANGE,
        IntegrationPermission.DELETE,
        IntegrationPermission.SYNC,
    ],
    UserPermission.VIEW: [
        UserPermission.ADD,
        UserPermission.CHANGE,
    ],
    ServiceAccountPermission.VIEW: [
        ServiceAccountPermission.ADD,
        ServiceAccountPermission.CHANGE,
    ],
    GroupPermission.VIEW: [GroupPermission.ASSIGN],
}


def dependencies_within(scope_permissions: list[str]) -> dict[str, list[str]]:
    """The dependencies checkable inside one permission set, keyed by requirement."""
    grantable = set(scope_permissions)
    return {
        required: [dependent for dependent in dependents if dependent in grantable]
        for required, dependents in PERMISSION_DEPENDENCIES.items()
        if required in grantable
    }
