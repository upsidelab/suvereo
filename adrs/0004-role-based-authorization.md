# ADR-0004: Role-based authorization with global and data-set scopes

## Status

Accepted

## Context

Authorization used Django's internals inconsistently:

- A Django admin panel existed, unmaintained but still reachable, and guarded by the `is_staff` flag.
- Our own admin checks were also based on `is_staff`.
- Django's groups and permissions tables were created and the permissions populated, but nothing used them.
- Access to data sets was limited by a many-to-many relationship between users and data sets. It could only say "has access or not", with no granularity.

## Decision

Authorization is made consistent and granular. Administrators can grant users granular access, either globally (for every data set) or scoped to one data set.

- **Role** — a named set of permissions. A role is either **global** (`GlobalRole`) or **data-set** (`DatasetRole`), and a data-set role applies within one data set.
- **Group** — a bucket of users and service accounts (`UserGroup`), so that assigning n people to n roles doesn't take n × n individual assignments. A group holds subjects only, and is granted roles.
- **Admin** — a flag on the account (`is_superuser`) that holds all permissions, including ones added in the future. It is deliberately not grantable through any permission code: a "may grant admin" permission would let its holder grant it to themselves. Only an admin can grant admin, or change an admin account.
- **Permissions** — the `auth.Permission` table is the only part of Django's authorization that is reused. Permissions are checked through `account.authorization`, with codes defined centrally in `permission_codenames.py`.
- **Django's own mechanisms are not used.** `auth.Group` is not used, because its design doesn't fit this model, and the `groups` field is removed from the user model. `RoleBackend` replaces Django's `ModelBackend` for permission lookups and resolves permissions through global roles only, whether assigned directly or through a group. Permissions assigned through Django's own mechanisms, as direct user permissions or through `auth.Group`, are ignored. The Django admin panel is not installed, and `is_staff` plays no part in authorization.
- **Permissions around permissions are grantable too.** There are separate permissions to add, change and assign users to roles (global and data-set ones separately), and to create, change and assign to groups.
- **Enforced on the API endpoints.** The exceptions are the few that have to be reachable without a login, such as login, token refresh, the OAuth callback and the API schema. On the others, an unauthenticated request gets 401, a request lacking the permission gets 403, and a request with no relationship to the data set gets 404.
- **The frontend mirrors the API.** The API returns the permissions the current user holds, and the UI reflects what that user can do: sections they cannot access are not displayed, and buttons for actions they cannot perform are hidden. The frontend only improves the experience, and the API enforces the rules.
- **Permissions depend on each other.** Granting a permission requires granting the ones it builds on, such as `view` of the same resource for any other permission on it. Assigning users to groups requires both the global and the data-set role-assign permissions, because adding someone to a group that has a role is the same as assigning them that role. Dependencies are transitive. They are defined in `PERMISSION_DEPENDENCIES`, on the principle that no capability may produce an effect its holder could not produce directly.

## Consequences

- Any endpoint is authorized through `account.authorization`, never through ad-hoc checks such as `is_staff` or role names.
- Holding the permissions to assign roles lets a user promote themselves. We accept this, because we should not restrict administrators from granting such roles. The UI warns when a role grants permissions that allow escalation.
- Permissions have to be kept consistent between the API and the frontend, which is an additional implementation cost. A new permission, or a change to what an endpoint requires, must be reflected in the frontend's permission handling too, otherwise the UI shows actions that the API rejects, or hides ones it allows.
- New permission codes are added to the central definitions and rules, together with their scope and dependencies.
- Code must not rely on Django's group or user-permission APIs for authorization, as they have no effect. Permissions are only read through global roles, and data-set permissions through the role-assignment models.
- Data-set access is checked by the helpers in `account.authorization.helpers`. A user with no relationship to a data set gets a 404 rather than a 403, so the data set's existence is not revealed.
