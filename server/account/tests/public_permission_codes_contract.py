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

DATASET_ADD = "dataset.add"
DATASET_CHANGE = "dataset.change"
DATASET_DELETE = "dataset.delete"
DATASET_VIEW = "dataset.view"

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

GROUP_VIEW = "group.view"
GROUP_ASSIGN = "group.assign"

DATASET_ROLE_VIEW = "dataset_role.view"
DATASET_ROLE_ASSIGN = "dataset_role.assign"

# Which capability each published string names. Pairing them here rather than only listing the
# strings is what catches a code that survives a rename but ends up attached to the wrong
# permission - the set of values alone would not notice.
PUBLIC_PERMISSION_CODES_CONTRACT: dict[str, str] = {
    PERMISSIONS.DATASET.ADD: DATASET_ADD,
    PERMISSIONS.DATASET.CHANGE: DATASET_CHANGE,
    PERMISSIONS.DATASET.DELETE: DATASET_DELETE,
    PERMISSIONS.DATASET.VIEW: DATASET_VIEW,
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
    PERMISSIONS.GROUP.VIEW: GROUP_VIEW,
    PERMISSIONS.GROUP.ASSIGN: GROUP_ASSIGN,
    PERMISSIONS.DATASET_ROLE.VIEW: DATASET_ROLE_VIEW,
    PERMISSIONS.DATASET_ROLE.ASSIGN: DATASET_ROLE_ASSIGN,
}

# The subset a dataset role can carry, as published under `?scope=dataset`. Spelled out rather
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
