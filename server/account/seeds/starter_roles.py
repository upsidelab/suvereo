"""The starter role set, offered by `manage.py seedroles`."""

from dataclasses import dataclass, field

from account.authorization import PERMISSIONS


@dataclass(frozen=True)
class StarterRole:
    name: str
    description: str
    permissions: list[str] = field(default_factory=list)


STARTER_GLOBAL_ROLES: list[StarterRole] = [
    StarterRole(
        name="Agent Interaction",
        description=(
            "Talk to any agent and run agentic executions, on any data set. Sees only its own "
            "conversations and executions, and can change nothing."
        ),
        permissions=[
            PERMISSIONS.DATA_SET.VIEW,
            PERMISSIONS.AGENT.VIEW,
            PERMISSIONS.CONVERSATION.CONVERSE,
            PERMISSIONS.AGENTIC_EXECUTION.CREATE,
        ],
    ),
    StarterRole(
        name="Management",
        description=(
            "Create, configure and delete data sets, the agents on them and the integrations that "
            "feed them, and run syncs. Cannot grant anyone access."
        ),
        permissions=[
            PERMISSIONS.DATA_SET.VIEW,
            PERMISSIONS.DATA_SET.ADD,
            PERMISSIONS.DATA_SET.CHANGE,
            PERMISSIONS.DATA_SET.DELETE,
            PERMISSIONS.AGENT.VIEW,
            PERMISSIONS.AGENT.ADD,
            PERMISSIONS.AGENT.CHANGE,
            PERMISSIONS.AGENT.DELETE,
            PERMISSIONS.INTEGRATION.VIEW,
            PERMISSIONS.INTEGRATION.ADD,
            PERMISSIONS.INTEGRATION.CHANGE,
            PERMISSIONS.INTEGRATION.DELETE,
            PERMISSIONS.INTEGRATION.SYNC,
        ],
    ),
    StarterRole(
        name="Access Management",
        description=(
            "Create and edit users, service accounts and groups, and grant them the roles that "
            "already exist. Cannot compose new roles or change what an existing one carries, and "
            "cannot make anyone an admin."
        ),
        permissions=[
            PERMISSIONS.USER.VIEW,
            PERMISSIONS.USER.ADD,
            PERMISSIONS.USER.CHANGE,
            PERMISSIONS.SERVICE_ACCOUNT.VIEW,
            PERMISSIONS.SERVICE_ACCOUNT.ADD,
            PERMISSIONS.SERVICE_ACCOUNT.CHANGE,
            PERMISSIONS.GROUP.VIEW,
            PERMISSIONS.GROUP.ADD,
            PERMISSIONS.GROUP.CHANGE,
            PERMISSIONS.GROUP.DELETE,
            PERMISSIONS.GROUP.ASSIGN,
            PERMISSIONS.GLOBAL_ROLE.VIEW,
            PERMISSIONS.GLOBAL_ROLE.ASSIGN,
            PERMISSIONS.DATA_SET_ROLE.VIEW,
            PERMISSIONS.DATA_SET_ROLE.ASSIGN,
            # `group.assign` statically requires both assign codes, and `data_set_role.assign`
            # requires this one - so managing group membership carries sight of every data set.
            PERMISSIONS.DATA_SET.VIEW,
        ],
    ),
]

STARTER_DATA_SET_ROLES: list[StarterRole] = [
    StarterRole(
        name="Agent Interaction",
        description=(
            "Talk to this data set's agents and run agentic executions on it. Sees only its own "
            "conversations and executions."
        ),
        permissions=[
            PERMISSIONS.AGENT.VIEW,
            PERMISSIONS.CONVERSATION.CONVERSE,
            PERMISSIONS.AGENTIC_EXECUTION.CREATE,
        ],
    ),
    StarterRole(
        name="Management",
        description=(
            "Configure, delete and sync a data set's agents and integrations. Cannot rename or "
            "delete the data set itself, and cannot grant anyone access to it."
        ),
        permissions=[
            PERMISSIONS.AGENT.VIEW,
            PERMISSIONS.AGENT.ADD,
            PERMISSIONS.AGENT.CHANGE,
            PERMISSIONS.AGENT.DELETE,
            PERMISSIONS.INTEGRATION.VIEW,
            PERMISSIONS.INTEGRATION.ADD,
            PERMISSIONS.INTEGRATION.CHANGE,
            PERMISSIONS.INTEGRATION.DELETE,
            PERMISSIONS.INTEGRATION.SYNC,
        ],
    ),
]
