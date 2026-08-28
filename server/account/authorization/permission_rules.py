from django.core.exceptions import ImproperlyConfigured

from .permission_codenames import (
    AgenticExecutionPermission,
    AgentPermission,
    ConversationPermission,
    DatasetPermission,
    DatasetRolePermission,
    GlobalRolePermission,
    IntegrationPermission,
    ServiceAccountPermission,
    UserGroupPermission,
    UserPermission,
)

_GLOBAL_ONLY_PERMISSIONS: list[str] = [
    *DatasetPermission,
    *UserPermission,
    *ServiceAccountPermission,
    *GlobalRolePermission,
    *DatasetRolePermission,
    *UserGroupPermission,
]

DATASET_SCOPE_PERMISSIONS: list[str] = [
    *AgentPermission,
    *IntegrationPermission,
    *ConversationPermission,
    *AgenticExecutionPermission,
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
        DatasetRolePermission.ASSIGN,
    ],
    AgentPermission.VIEW: [
        AgentPermission.ADD,
        AgentPermission.CHANGE,
        AgentPermission.DELETE,
        ConversationPermission.CONVERSE,
        AgenticExecutionPermission.CREATE,
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
        GlobalRolePermission.ASSIGN,
        DatasetRolePermission.ASSIGN,
        UserGroupPermission.ASSIGN,
    ],
    ServiceAccountPermission.VIEW: [
        ServiceAccountPermission.ADD,
        ServiceAccountPermission.CHANGE,
        GlobalRolePermission.ASSIGN,
        DatasetRolePermission.ASSIGN,
        UserGroupPermission.ASSIGN,
    ],
    GlobalRolePermission.VIEW: [
        GlobalRolePermission.ADD,
        GlobalRolePermission.CHANGE,
        GlobalRolePermission.DELETE,
        GlobalRolePermission.ASSIGN,
    ],
    DatasetRolePermission.VIEW: [
        DatasetRolePermission.ADD,
        DatasetRolePermission.CHANGE,
        DatasetRolePermission.DELETE,
        DatasetRolePermission.ASSIGN,
    ],
    UserGroupPermission.VIEW: [
        UserGroupPermission.ADD,
        UserGroupPermission.CHANGE,
        UserGroupPermission.DELETE,
        UserGroupPermission.ASSIGN,
        GlobalRolePermission.ASSIGN,
        DatasetRolePermission.ASSIGN,
    ],
    # Adding someone to a group hands them the group's own grants, so `group.assign` cannot stand
    # alone: no capability may produce an effect its holder could not have produced directly.
    GlobalRolePermission.ASSIGN: [UserGroupPermission.ASSIGN],
    DatasetRolePermission.ASSIGN: [UserGroupPermission.ASSIGN],
}


def build_transitive_dependencies(dependencies: dict[str, list[str]]) -> dict[str, list[str]]:
    """`dependencies` with every requirement's own requirements folded into its dependents.

    Rejects a cyclic map rather than closing over it. A cycle has a well-defined closure - every
    permission in it requires all the others, so they can only ever be granted together - but that
    is never what a requirement is meant to express, and it would surface as a code that
    inexplicably drags others along rather than as the authoring mistake it is.
    """
    requirements: dict[str, set[str]] = {}
    for required, dependents in dependencies.items():
        for dependent in dependents:
            requirements.setdefault(dependent, set()).add(required)

    widened = True
    while widened:
        widened = False
        for dependent, required in requirements.items():
            reached = required | {step for code in required for step in requirements.get(code, ())}
            if reached != required:
                requirements[dependent] = reached
                widened = True

    cyclic = sorted(dependent for dependent, required in requirements.items() if dependent in required)
    if cyclic:
        raise ImproperlyConfigured(
            f"PERMISSION_DEPENDENCIES is cyclic: {', '.join(cyclic)} transitively require themselves."
        )

    closure: dict[str, list[str]] = {required: [] for required in dependencies}
    for dependent, required in requirements.items():
        for code in required:
            closure[code].append(dependent)
    return {required: sorted(dependents) for required, dependents in closure.items()}


TRANSITIVE_PERMISSION_DEPENDENCIES: dict[str, list[str]] = build_transitive_dependencies(PERMISSION_DEPENDENCIES)


def dependencies_within(scope_permissions: list[str]) -> dict[str, list[str]]:
    """The dependencies checkable inside one permission set, keyed by requirement.

    Transitive, so one response names everything a permission needs
    """
    grantable = set(scope_permissions)
    return {
        required: [dependent for dependent in dependents if dependent in grantable]
        for required, dependents in TRANSITIVE_PERMISSION_DEPENDENCIES.items()
        if required in grantable
    }
