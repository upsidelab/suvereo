"""The public permission vocabulary, written out by hand.

These are the strings the frontend sends and receives. The application never declares them
literally - `PUBLIC_CODES` derives them from the entity and member names in `PERMISSIONS`, which
makes a missing or mismatched entry structurally impossible but also means the wire format has no
textual declaration anywhere in `server/`. This module is that declaration, and
`test_public_permission_codes_contract.py` is what holds the two together.

**Do not import `PUBLIC_CODES` here, and do not build these values from it.** The whole point is
that they are an independent, hand-written record of what was published. A test that reaches for
the derived map instead of these constants will keep passing through a rename that breaks every
frontend caller - the two look interchangeable at the call site and guarantee opposite things:

    AGENT_CHANGE                              # "agent.change", whatever the derivation now does
    PUBLIC_CODES[PERMISSIONS.AGENT.CHANGE]    # whatever the derivation now does

Changing anything below is changing a published contract. That is the intended friction: it should
be a deliberate, reviewable diff rather than a side effect of renaming an enum member.
"""

from account.authorization import PERMISSIONS

DATASET_ADD = "data_set.add"
DATASET_CHANGE = "data_set.change"
DATASET_DELETE = "data_set.delete"
DATASET_VIEW = "data_set.view"

AGENT_ADD = "agent.add"
AGENT_CHANGE = "agent.change"
AGENT_DELETE = "agent.delete"
AGENT_VIEW = "agent.view"

INTEGRATION_ADD = "integration.add"
INTEGRATION_CHANGE = "integration.change"
INTEGRATION_DELETE = "integration.delete"
INTEGRATION_VIEW = "integration.view"
INTEGRATION_SYNC = "integration.sync"

CONVERSATION_CONVERSE = "conversation.converse"
CONVERSATION_VIEW_ALL = "conversation.view_all"

AGENTIC_EXECUTION_CREATE = "agentic_execution.create"
AGENTIC_EXECUTION_VIEW_ALL = "agentic_execution.view_all"

USER_ADD = "user.add"
USER_CHANGE = "user.change"
USER_VIEW = "user.view"

SERVICE_ACCOUNT_ADD = "service_account.add"
SERVICE_ACCOUNT_CHANGE = "service_account.change"
SERVICE_ACCOUNT_VIEW = "service_account.view"

GLOBAL_ROLE_VIEW = "global_role.view"
GLOBAL_ROLE_ADD = "global_role.add"
GLOBAL_ROLE_CHANGE = "global_role.change"
GLOBAL_ROLE_DELETE = "global_role.delete"
GLOBAL_ROLE_ASSIGN = "global_role.assign"

DATASET_ROLE_VIEW = "data_set_role.view"
DATASET_ROLE_ADD = "data_set_role.add"
DATASET_ROLE_CHANGE = "data_set_role.change"
DATASET_ROLE_DELETE = "data_set_role.delete"
DATASET_ROLE_ASSIGN = "data_set_role.assign"

GROUP_VIEW = "group.view"
GROUP_ADD = "group.add"
GROUP_CHANGE = "group.change"
GROUP_DELETE = "group.delete"
GROUP_ASSIGN = "group.assign"

# Which capability each published string names. Pairing them here rather than only listing the
# strings is what catches a code that survives a rename but ends up attached to the wrong
# permission - the set of values alone would not notice.
PUBLIC_PERMISSION_CODES_CONTRACT: dict[str, str] = {
    PERMISSIONS.DATA_SET.ADD: DATASET_ADD,
    PERMISSIONS.DATA_SET.CHANGE: DATASET_CHANGE,
    PERMISSIONS.DATA_SET.DELETE: DATASET_DELETE,
    PERMISSIONS.DATA_SET.VIEW: DATASET_VIEW,
    PERMISSIONS.AGENT.ADD: AGENT_ADD,
    PERMISSIONS.AGENT.CHANGE: AGENT_CHANGE,
    PERMISSIONS.AGENT.DELETE: AGENT_DELETE,
    PERMISSIONS.AGENT.VIEW: AGENT_VIEW,
    PERMISSIONS.INTEGRATION.ADD: INTEGRATION_ADD,
    PERMISSIONS.INTEGRATION.CHANGE: INTEGRATION_CHANGE,
    PERMISSIONS.INTEGRATION.DELETE: INTEGRATION_DELETE,
    PERMISSIONS.INTEGRATION.VIEW: INTEGRATION_VIEW,
    PERMISSIONS.INTEGRATION.SYNC: INTEGRATION_SYNC,
    PERMISSIONS.CONVERSATION.CONVERSE: CONVERSATION_CONVERSE,
    PERMISSIONS.CONVERSATION.VIEW_ALL: CONVERSATION_VIEW_ALL,
    PERMISSIONS.AGENTIC_EXECUTION.CREATE: AGENTIC_EXECUTION_CREATE,
    PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL: AGENTIC_EXECUTION_VIEW_ALL,
    PERMISSIONS.USER.ADD: USER_ADD,
    PERMISSIONS.USER.CHANGE: USER_CHANGE,
    PERMISSIONS.USER.VIEW: USER_VIEW,
    PERMISSIONS.SERVICE_ACCOUNT.ADD: SERVICE_ACCOUNT_ADD,
    PERMISSIONS.SERVICE_ACCOUNT.CHANGE: SERVICE_ACCOUNT_CHANGE,
    PERMISSIONS.SERVICE_ACCOUNT.VIEW: SERVICE_ACCOUNT_VIEW,
    PERMISSIONS.GLOBAL_ROLE.VIEW: GLOBAL_ROLE_VIEW,
    PERMISSIONS.GLOBAL_ROLE.ADD: GLOBAL_ROLE_ADD,
    PERMISSIONS.GLOBAL_ROLE.CHANGE: GLOBAL_ROLE_CHANGE,
    PERMISSIONS.GLOBAL_ROLE.DELETE: GLOBAL_ROLE_DELETE,
    PERMISSIONS.GLOBAL_ROLE.ASSIGN: GLOBAL_ROLE_ASSIGN,
    PERMISSIONS.DATA_SET_ROLE.VIEW: DATASET_ROLE_VIEW,
    PERMISSIONS.DATA_SET_ROLE.ADD: DATASET_ROLE_ADD,
    PERMISSIONS.DATA_SET_ROLE.CHANGE: DATASET_ROLE_CHANGE,
    PERMISSIONS.DATA_SET_ROLE.DELETE: DATASET_ROLE_DELETE,
    PERMISSIONS.DATA_SET_ROLE.ASSIGN: DATASET_ROLE_ASSIGN,
    PERMISSIONS.GROUP.VIEW: GROUP_VIEW,
    PERMISSIONS.GROUP.ADD: GROUP_ADD,
    PERMISSIONS.GROUP.CHANGE: GROUP_CHANGE,
    PERMISSIONS.GROUP.DELETE: GROUP_DELETE,
    PERMISSIONS.GROUP.ASSIGN: GROUP_ASSIGN,
}

# The subset a data set role can carry, as published under `?scope=data_set`. Spelled out rather
# than filtered out of the map above, so moving a permission between scopes is a visible edit here
# too - a scope change is as much a frontend contract change as a rename is.
DATASET_SCOPED_CONTRACT: frozenset[str] = frozenset(
    {
        AGENT_ADD,
        AGENT_CHANGE,
        AGENT_DELETE,
        AGENT_VIEW,
        INTEGRATION_ADD,
        INTEGRATION_CHANGE,
        INTEGRATION_DELETE,
        INTEGRATION_VIEW,
        INTEGRATION_SYNC,
        CONVERSATION_CONVERSE,
        CONVERSATION_VIEW_ALL,
        AGENTIC_EXECUTION_CREATE,
        AGENTIC_EXECUTION_VIEW_ALL,
    }
)
