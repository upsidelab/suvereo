# Roles and Groups

Access in Suvereo is granted through roles. A role is a named set of permissions, such as "view agents" or "start agentic executions". Roles are assigned to users and service accounts, directly or through groups. Admins are the exception: they hold every permission without roles, see [Admins](/docs/management/users#admins). For how permissions affect the pages of this section, see the [overview](/docs/management).

## Roles

There are two kinds of roles, which differ in where their permissions apply.

- **Global roles** apply to the whole system. A permission granted by a global role, such as "view agents", holds on every data set. Global roles also carry the permissions for administering the system itself: managing users, service accounts, roles and groups.
- **Data set roles** apply to one data set. The same role can be granted on several data sets, separately on each, and carries only permissions that make sense inside a data set, such as working with its agents and integrations.

Both kinds are managed under **Manage** → **Roles**, on the **Global Roles** and **Data Set Roles** tabs. To create a role, use the button above the list on its tab, name the role and tick the permissions it carries. Editing a role changes what everyone holding it can do. Deleting a role removes its permissions from everyone who held it, and does not delete them or the groups that held it.

Some permissions depend on others, for example changing agents requires viewing them. The role editor shows the dependencies and does not accept a role that misses one. It also asks for confirmation when a role includes permissions that let its holder grant themselves further access, such as assigning roles.

### Granting a global role

On the **Global Roles** tab, open a role to see who holds it and to add users, service accounts or groups to it.

### Granting a data set role

A data set role is granted on a specific data set, from **Manage** → **Data Sets** → **Manage Access**, see [Controlling Access](/docs/management/data-sets#controlling-access).

A user who holds no role on a data set does not see it.

## Service accounts

A service account is an identity for programmatic API access, authorized through roles in the same way as a user. Roles are granted to it from the same places as for users. Creating accounts and their API tokens is described in [Managing API Keys](/docs/integrate/manage-api-keys).

## Groups

A group is a collection of users and service accounts that is granted roles as one. A group has no permissions of its own: every member holds the roles the group holds, and people added later hold them too. Groups save assigning the same roles to each person one by one.

Groups are managed on the **Groups** tab under **Manage** → **Roles**. A group has members, and can be granted global roles and data set roles. Because adding someone to a group gives them its roles, managing group membership requires the permission to assign both kinds of roles.

## Permissions

Roles are built from the permissions below. The code is the name used by the API. The scope tells where a permission can be put: global roles can carry every permission, data set roles only the ones marked "Global or data set". Making someone an admin is not a permission, only an admin can do it.

| Permission | Allows | Scope | Requires |
|---|---|---|---|
| `data_set.view` | See data sets | Global | |
| `data_set.add` | Create data sets | Global | `data_set.view` |
| `data_set.change` | Edit data sets | Global | `data_set.view` |
| `data_set.delete` | Delete data sets | Global | `data_set.view` |
| `agent.view` | See agents | Global or data set | `data_set.view` |
| `agent.add` | Add agents | Global or data set | `agent.view` |
| `agent.change` | Edit agents | Global or data set | `agent.view` |
| `agent.delete` | Delete agents | Global or data set | `agent.view` |
| `integration.view` | See integrations | Global or data set | `data_set.view` |
| `integration.add` | Add integrations | Global or data set | `integration.view` |
| `integration.change` | Edit integrations | Global or data set | `integration.view` |
| `integration.delete` | Delete integrations | Global or data set | `integration.view` |
| `integration.sync` | Run integration syncs | Global or data set | `integration.view` |
| `conversation.converse` | Talk to agents, and see your own conversations | Global or data set | `agent.view` |
| `conversation.view_all` | See everyone's conversations | Global or data set | `data_set.view` |
| `agentic_execution.create` | Start agentic executions, and see your own | Global or data set | `agent.view` |
| `agentic_execution.view_all` | See everyone's agentic executions | Global or data set | `data_set.view` |
| `user.view` | See users | Global | |
| `user.add` | Create users | Global | `user.view` |
| `user.change` | Edit users | Global | `user.view` |
| `service_account.view` | See service accounts | Global | |
| `service_account.add` | Create service accounts | Global | `service_account.view` |
| `service_account.change` | Edit service accounts | Global | `service_account.view` |
| `global_role.view` | See global roles | Global | |
| `global_role.add` | Create global roles | Global | `global_role.view` |
| `global_role.change` | Edit global roles | Global | `global_role.view` |
| `global_role.delete` | Delete global roles | Global | `global_role.view` |
| `global_role.assign` | Grant global roles to users, service accounts and groups | Global | `global_role.view`, `user.view`, `service_account.view`, `group.view` |
| `data_set_role.view` | See data set roles | Global | |
| `data_set_role.add` | Create data set roles | Global | `data_set_role.view` |
| `data_set_role.change` | Edit data set roles | Global | `data_set_role.view` |
| `data_set_role.delete` | Delete data set roles | Global | `data_set_role.view` |
| `data_set_role.assign` | Grant data set roles to users, service accounts and groups | Global | `data_set_role.view`, `data_set.view`, `user.view`, `service_account.view`, `group.view` |
| `group.view` | See groups | Global | |
| `group.add` | Create groups | Global | `group.view` |
| `group.change` | Edit groups | Global | `group.view` |
| `group.delete` | Delete groups | Global | `group.view` |
| `group.assign` | Add users and service accounts to groups | Global | `group.view`, `global_role.assign`, `data_set_role.assign` |

Requirements chain: a permission also needs everything its requirements need. For example, `agent.add` needs `agent.view`, which needs `data_set.view`. The role editor does not accept a role that misses a requirement. `group.assign` requires both role-assign permissions because adding someone to a group gives them the group's roles.

## Starter roles

A new instance has no roles besides admin access. The `seedroles` management command creates a starter set, in both a global and, where it applies, a data set version:

```bash
cd server
./manage.py seedroles
```

| Role | Global role | Data set role |
|---|---|---|
| Agent Interaction | Talk to agents and run agentic executions on any data set. Sees only its own conversations and executions. | The same, on one data set. |
| Management | Create, configure and delete data sets, their agents and integrations, and run syncs. Cannot grant access. | Configure, delete and sync one data set's agents and integrations. Cannot rename or delete the data set or grant access. |
| Access Management | Create and edit users, service accounts and groups, and grant the roles that exist. Cannot create roles, change what a role carries or make anyone an admin. | None. |

The command can be run again safely: a role with an existing name is left unchanged and reported as matching or differing from the starter set. `--dry-run` shows what would happen without writing anything. The starter roles are ordinary roles, and can be edited or deleted afterwards.

## Permissions in the UI and the API

The UI and the API apply the same permissions. In the UI, sections a person cannot access are hidden, buttons for actions they cannot perform are hidden, and some pages, such as a data set's configuration, open read-only. The API enforces the rules: a request without a valid login is rejected with `401`, one that lacks a permission with `403`, and one for a data set the caller has no role on with `404`, so the existence of the data set is not revealed.
