# Permissions implementation plan (actionable, grounded in `main`)

Companion to `permissions-rewrite-plan.md` (principles/target state, written before this file). That doc says what we're *not* recreating from `feature/ent-333-...`. This doc says what to actually build against `main`'s real current code, and is further shaped by `## Permissions Note` (the entity/capability list a human wrote directly — reproduced in full at the bottom of this file). Where the note conflicts with an earlier decision, the note wins; those reversals are called out explicitly below.

**Delivery shape:** one phase per entity from the note, each landing as its own PR and independently testable before the next starts (see "Confirmed design decisions" #5). **Frontend is a separate branch/PR, done last, after every backend phase below has merged** — it targets the final API shape once instead of chasing eight rounds of backend changes underneath it.

## `main`'s actual baseline (what we're building on top of)

- `User(AbstractUser)`: `email` (unique, `USERNAME_FIELD`), `is_service_account`, plus stock `is_staff`/`is_superuser`/`is_active`/`groups`/`user_permissions` (unused today except `is_staff`).
- **`is_staff` is already the sole "admin" gate everywhere** — DRF's `IsAdminUser` on ~10 views, `User.has_dataset_access()`, and pervasively on the frontend (`account.isStaff` in nav gating, login redirect, route protection).
- `DataSet.users` — plain `ManyToManyField(User, related_name="data_sets")`. `User.has_dataset_access(dataset)` = `self.is_staff or dataset in self.data_sets`. This is the **entire** access-control model today: binary membership + global staff bypass, no roles, no read/write distinction.
- Full CRUD screens already exist and work: Users (`/users`), Service Accounts (`/service-accounts`), dataset membership (`/data-sets/:id/users`). No Groups/Roles UI exists anywhere on `main` — confirmed absent.
- `apps.get_models()` defaults: `DataSet`, `Agent`, `Integration`, `User` all still have Django's default `add_x`/`change_x`/`delete_x`/`view_x` permissions (none of these models override `default_permissions`) — **these rows already exist in `auth_permission`, unused.** `Conversation` and `AgenticExecution` have no custom permissions declared, but (same as above) their four Django-default CRUD codenames already exist as unused rows too.
- Confirmed gaps in today's enforcement (to close phase by phase below, not just refactor around):
  1. `AgentView`/`AgentDetailsView` (`agent/views.py`) — **zero dataset-access enforcement**, `IsAuthenticated` only. Any logged-in user can CRUD any agent on any dataset.
  2. `agentic_execution` views, especially `StartAgenticExecutionView` — same gap, no dataset check before starting an execution.
  3. `ConversationView.post` fetches the conversation by id with no `user=` filter — a dataset co-member (not the owner) can post into someone else's conversation.
  4. `MessageFeedbackView` — no access control at all beyond `IsAuthenticated`.
  5. Inconsistent staff-vs-member gating: `DataSetDetailView`/`DataSetUserListView` require `IsAdminUser` (staff-only), while `Integration` CRUD/sync and `Entity` records only require `has_dataset_access` (staff OR plain member).
  6. No oversight path exists anywhere for "see everyone's conversations" or "see everyone's agentic executions" — `ConversationListView.get_queryset` and `AgenticExecutionListView`/`DetailView` hard-filter to `user=request.user` / `conversation__user=request.user` for *every* caller, admin included.

## The Permissions Note, and what it changes

The note (full text at the bottom) groups capabilities by entity — Dataset, Agent, Integration, Conversation, Agentic Executions, Users, Service Account, Permission Management — and closes with: *"All permissions are global. Agent / Integration / Conversation / Agentic Executions also have dataset-specific counterparts."* Two things in it needed a decision before the rest of this plan could be written; both are resolved below and drive the design that follows.

### Confirmed design decisions

1. **Dataset permissions are global-only.** The note's closing line names exactly four entities as having a dataset-specific counterpart — Dataset isn't one of them. So `add_dataset`/`change_dataset`/`delete_dataset`/`view_dataset` are only ever checked globally (`user.has_perm(...)`, which already covers the admin bypass — see the reversed decision below); there's no per-dataset grant of these codenames. An ordinary member's ability to see *their* dataset's config/catalog comes for free from simply **holding any role assignment on that dataset** (`DatasetUserRoleAssignment`/`DatasetGroupRoleAssignment` row exists), not from a separately-scoped `view_dataset` grant. A global `view_dataset` grantee is an oversight role that can see every dataset's config/catalog, member or not. This is a simplification of the earlier plan's `datasets_visible_to`, not an addition.
2. **Service Account gets its own CRUD codenames, separate from User**, reversing decision #3 below. There's no separate `ServiceAccount` model on `main` (confirmed — no proxy models exist anywhere in the codebase) and introducing one is out of scope here, so `add_serviceaccount`/`change_serviceaccount`/`delete_serviceaccount`/`view_serviceaccount` are declared as bespoke entries in `User.Meta.permissions`, alongside (not replacing) the Django-default `add_user`/`change_user`/`delete_user`/`view_user` the same model already carries. Same table, same model, two independently-grantable permission sets — granting one says nothing about the other.
3. **Conversation and Agentic Execution "view all" need no new codenames.** Both models already carry an unused, Django-default `view_conversation` / `view_agenticexecution` permission (neither model sets `default_permissions = ()`). Rather than invent `view_all_conversations` from scratch, this plan repurposes those existing defaults as exactly that oversight permission — same "already exists, just put it to use" idiom the rest of this doc leans on. This reverses decision #4 below (which rejected a "view all" conversations feature outright; the note asks for it explicitly, for both entities).
4. **Integration's "Sync" is its own codename, not folded into `change_integration`.** The note lists CRUD and Sync as separate bullets under Integration. Bespoke `sync_integration`, declared in `Integration.Meta.permissions`, dual-scope like the rest of Integration's codenames.
5. **Phased, one-entity-at-a-time delivery**, chosen so each phase is testable in isolation without the next entity's work landing first — see "Phased delivery order."

### Decisions from the original draft that still stand

1. ~~**Admin flag stays `is_staff`, not `is_superuser`.**~~ **Reversed during Phase 1 implementation.** `is_superuser` is what Django actually built for "bypass every permission check": `PermissionsMixin.has_perm()` shortcuts to `True` for an active superuser *before* it ever consults `user_permissions`/`groups`. That means every helper below gets the bypass for free just by calling `has_perm(...)` — no hand-rolled `is_staff or ...` (nor `is_superuser or ...`) at any call site, which is a genuine simplification, not just a relabeling. `is_staff` reverts to Django's own native meaning (can open `/admin`) and carries zero authorization weight anywhere in this app; DRF's built-in `IsAdminUser` (which checks `is_staff`) is replaced by a bespoke `IsAdmin` (checks `is_superuser` directly) at every admin-of-admin surface that doesn't go through `has_perm`. Externally, neither Django flag is named directly: the API and frontend only ever expose `is_admin` / `isAdmin` — every serializer field is declared as `is_admin = serializers.BooleanField(source="is_superuser")`, so the wire contract doesn't hint that this is backed by Django's own `is_superuser` field (which would otherwise leak an implementation detail — e.g. "they're on Django" — to API consumers) while internal code (`validated_data`, `instance.is_superuser = ...`) keeps reading/writing the real model attribute unchanged.
2. **No `configure_models` permission** still stands — no new bespoke codename is introduced for these views. ~~`IsAuthenticated`-only~~ **partially reversed during Phase 1 implementation.** `ConfigView`/`ConfigLanguageModelView`/`ConfigEmbeddingModelView` are read-only catalogs of available provider/model names, not a mutation on any resource, and `IsAdminUser` is still dropped — but they're not left fully open to any authenticated user either: the only caller is `data-set-form.tsx` (New/Edit Data Set), so a user who can neither create nor edit a dataset has no legitimate use for this catalog and gets nothing from it. Gated on the existing `catalog.add_dataset` **or** `catalog.change_dataset` (global, any-of — see `any_permission_required` below), reusing Dataset's own CRUD codenames rather than inventing a new one, consistent with the rest of this doc's "already exists, just put it to use" idiom.
3. ~~**`manage_users`/`manage_service_accounts` collapse into one.**~~ **Reversed by decision #2 above** — the note treats them as separate entities, so they get separate codenames after all.
4. ~~**No `view_all_conversations`.**~~ **Reversed by decision #3 above** — the note asks for it explicitly (and its Agentic Executions twin), satisfied by repurposing the existing default `view_*` codenames rather than inventing a new one.

## Final permission set (23 codenames, no scope duplication)

Global-only (no per-dataset counterpart):

| Codename | Where declared |
|---|---|
| `catalog.add_dataset` / `change_dataset` / `delete_dataset` / `view_dataset` | already exist (Django default) |
| `account.add_user` / `change_user` / `delete_user` / `view_user` | already exist (Django default) |
| `account.add_serviceaccount` / `change_serviceaccount` / `delete_serviceaccount` / `view_serviceaccount` | **new** — bespoke, added to `User.Meta.permissions` |
| `auth.add_group` / `change_group` / `delete_group` / `view_group` | already exist (Django default, stock `auth.Group`) |
| `account.add_datasetrole` / `change_datasetrole` / `delete_datasetrole` / `view_datasetrole` | already exist once `DatasetRole` model is created (Django default) |

Dual-scope (global **or** per-dataset, via `has_dataset_perm`):

| Codename | Where declared |
|---|---|
| `agent.add_agent` / `change_agent` / `delete_agent` / `view_agent` | already exist (Django default) |
| `catalog.add_integration` / `change_integration` / `delete_integration` / `view_integration` | already exist (Django default) |
| `catalog.sync_integration` | **new** — bespoke, added to `Integration.Meta.permissions` |
| `agent.converse` | **new** — bespoke, added to `Conversation.Meta.permissions` |
| `agent.view_conversation` | already exists (Django default) — **repurposed** as "view all conversations" |
| `agent.add_agenticexecution` | already exists (Django default) — doubles as "Create" (own-history access implied) |
| `agent.view_agenticexecution` | already exists (Django default) — **repurposed** as "view all executions" |

Not a permission codename at all: **"only admin can give admin, or deactivate admin"** is a hardcoded `request.user.is_superuser` gate plus the self-lockout guard (see Phase 8) — deliberately not delegable, same reasoning as the admin-of-admin surfaces below. Externally this flag is never called `is_superuser`; the API/frontend name is `is_admin`/`isAdmin` (see the reversed decision above).

`default_permissions` is left alone (not set to `()`) on every model — the unused Django-default rows are being put to work, not pruned.

## New models (`account` app)

```
DatasetRole
  name            CharField, unique
  permissions     ManyToManyField(Permission)

DatasetUserRoleAssignment
  user     FK(User, on_delete=CASCADE)
  dataset  FK(catalog.DataSet, on_delete=CASCADE)
  role     FK(DatasetRole, on_delete=PROTECT)
  unique_together = ("user", "dataset")

DatasetGroupRoleAssignment
  group    FK(auth.Group, on_delete=CASCADE)
  dataset  FK(catalog.DataSet, on_delete=CASCADE)
  role     FK(DatasetRole, on_delete=PROTECT)
  unique_together = ("group", "dataset")
```

No `created_at`/`updated_at` on any of these three, deliberately — Django's own `auth.Group` and `auth.Permission` (and the M2M/through tables binding them) carry no timestamps either, and these three tables are modeled as peers of that machinery, not as a different tier with its own conventions. See "Deferred: timestamps + `granted_by`" below.

`on_delete=CASCADE` on `dataset` closes the guardian-style leak by construction — deleting a `DataSet` removes its role assignments as a DB-level cascade, not an app-code cleanup call. `role` is `PROTECT` so a role can't be deleted while still assigned anywhere (surfaced as a "N datasets/groups use this role" check in Phase 8).

### Deferred: timestamps + `granted_by`

Raised and reverted during Phase 0 implementation: `created_at`/`updated_at` on `DatasetRole`, `created_at` on the two assignment models. Reverted because Django's own permission-assignment plumbing (`Group`, `Permission`, `User.groups`, `User.user_permissions`, and `Group.permissions`) has none of this, and these three tables sit at that same layer — adding it selectively here would make our tables inconsistent with the primitives they extend, not more consistent.

If auditability (when a role was created/modified, when a grant was made, *who* made it) becomes a real requirement, it should land as **one uniform pass across both our tables and Django's built-ins** — not bolted onto just the new models. That likely means a separate, generic mechanism (e.g. a lightweight audit-log model recording actor/action/target/timestamp) rather than ad hoc `created_at`/`granted_by` columns scattered per table, since `auth.Group`/`auth.Permission` can't be altered to carry new columns without forking Django's own migrations. TBD, own task, not scoped to this plan.

`Group` (global bundling — the note's "general" groups) needs no model changes — it's Django's stock model, already installed, just unused. `DatasetRole` is the note's "dataset-specific" group.

## Enforcement helpers (`account/authorization.py`, new file — built incrementally, see phases)

No `user.is_staff or ...` / `user.is_superuser or ...` bypass appears anywhere below — `has_perm(...)` already returns `True` unconditionally for an active superuser, for free (see the reversed decision above), so every helper just calls it directly:

```python
def is_dataset_member(user, dataset) -> bool:
    """True if `user` has ANY role assignment on `dataset` (directly or via a group),
    or holds global `catalog.view_dataset` (superusers included, for free). Backs Dataset
    visibility only — Dataset permissions are global-only, so per-dataset "can I see this
    one" is presence-based, not tied to a specific codename."""
    if user.has_perm("catalog.view_dataset"):
        return True
    if DatasetUserRoleAssignment.objects.filter(user=user, dataset=dataset).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(group__in=user.groups.all(), dataset=dataset).exists()


def datasets_visible_to(user):
    if user.has_perm("catalog.view_dataset"):
        return DataSet.objects.all()
    return DataSet.objects.filter(
        Q(datasetuserroleassignment__user=user) | Q(datasetgrouproleassignment__group__in=user.groups.all())
    ).distinct()


def has_dataset_perm(user, codename: str, dataset) -> bool:
    """For the four dual-scope entities (Agent/Integration/Conversation/AgenticExecution) only."""
    if user.has_perm(codename):
        return True
    bare = codename.split(".")[-1]
    if DatasetUserRoleAssignment.objects.filter(
        user=user, dataset=dataset, role__permissions__codename=bare
    ).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(
        group__in=user.groups.all(), dataset=dataset, role__permissions__codename=bare
    ).exists()
```

Phase 1 shipped the global-only case as a pair of method decorators rather than the permission class originally sketched here, since several call sites (e.g. `DataSetDetailView`) need a different codename per HTTP method on the same view. `permission_required` is the single-codename gate; `any_permission_required` is its any-of counterpart, needed for the Config views (see decision #2 above), which are gated on `add_dataset` **or** `change_dataset` rather than a single codename. An `all_permissions_required` (every one of several codenames, not just one) is a natural next addition if a view ever needs it — no call site does yet, so it isn't built. Names follow Django's own `permission_required` convention (`django.contrib.auth.decorators`) deliberately — its actual *implementation* isn't reused, since it's redirect-based (wrong for an API even with `raise_exception=True`, which still collapses 401-vs-403 into a flat 403 — DRF's `self.permission_denied()` gets this right) and its multi-codename form is AND-only (`has_perms`), not the any-of semantics needed here:

```python
def permission_required(codename: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not self.request.user.has_perm(codename):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)
        return wrapper
    return decorator


def any_permission_required(*codenames: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not any(self.request.user.has_perm(codename) for codename in codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)
        return wrapper
    return decorator
```

`HasPermission` (the class form) may still be worth introducing in Phase 6/7 for the views that *are* uniformly one-codename-per-method — not decided yet, not blocking.

Separately, one small DRF permission class for the admin-of-admin surfaces, which deliberately check `is_superuser` directly rather than `has_perm(...)`:

```python
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
```

Global admin-of-admin surfaces (Groups CRUD, DatasetRoles CRUD, the permission listing endpoint, dataset-role-assignment endpoints) stay `IsAdmin`-only — a delegable "manage roles" permission would let its holder grant themselves anything. Their Django-default codenames still exist in `auth_permission` (same "unused row, hardcoded gate" idiom as `is_superuser` itself here), they're just never checked via `has_perm`.

## `DataSetUserListView`/`DataSetUserView` during the transition

These are `main`'s existing membership-management endpoints (`/data_sets/<id>/users/`), backed today by the `DataSet.users` M2M. Phase 0 drops that M2M with no replacement backing store (see "Migration strategy" below) — there's no seeded role yet for these endpoints to assign, so they're stubbed to no-ops instead (empty list on GET, no-op success on add/remove). They're replaced for real in Phase 8, once `dataset_access.py` and a real role-choice UI exist.

## Migration strategy

This plan is being built against a **clean database** — there's no production data yet, so Phase 0 does not try to preserve `DataSet.users` membership across the cutover. The M2M is simply dropped (`RemoveField`); no backfill migration runs, and no default role is seeded to backfill into. `User.has_dataset_access()` is stubbed to unconditionally `return True` in the meantime (see Phase 0) rather than backed by a real membership check, since there'd be nothing meaningful to check yet.

Whether a *real* backward-compatible migration path (preserving existing dataset memberships across this refactor) is ever needed is explicitly **left open** — this is a major version, and the data schema may not need to stay compatible with pre-refactor deployments at all. That's a call for the tech lead, not something baked into this plan. If it does turn out to matter, a backfill migration (seed a role, walk `DataSet.users`, create matching `DatasetUserRoleAssignment` rows) can be written and inserted before whichever phase first depends on real per-dataset role data — most likely Phase 1, since `catalog/entities/views.py`'s Dataset View check is the first call site to leave `has_dataset_access` behind.

No default "Member" (or any other) role is auto-seeded anywhere in this plan. Roles are created and populated explicitly through Phase 8's admin UI (`dataset_roles.py`/`dataset_access.py`) once it exists; each phase's own data migration only adds a *codename* to `auth_permission` (via `Meta.permissions` or an existing Django default) — it never bundles codenames into a pre-made role on anyone's behalf.

## Phased delivery order

Each phase lands as its own PR, is independently testable, and (other than Phase 0) touches exactly one entity from the note.

---

### Phase 0 — Foundational data model & helpers (schema + authorization only)

Deliberately thin: adds the new tables and the `account/authorization.py` helpers with **nothing wired up to them yet** — no call site is upgraded to use them in this phase. `User.has_dataset_access()` is **stubbed, not deleted and not redefined against the new tables**:

```python
def has_dataset_access(self, dataset):
    """Temporary stub: dataset access is granted unconditionally until each entity's own phase
    replaces this call site with a real has_dataset_perm(...) (or is_dataset_member(...)) check.
    Delete this method once its last caller is gone — do not add new callers."""
    return True
```

Its three existing call sites (`agent/views.py`, `catalog/integrations/views.py`, `catalog/entities/views.py`) keep compiling against this stub once the M2M they used to depend on is gone. `has_dataset_access` is retired **one call site at a time, by whichever phase owns that entity** — not all at once, and not via an intermediate `is_dataset_member` hop:
  - `catalog/entities/views.py` → Phase 1 replaces the call with `is_dataset_member(request.user, dataset)` directly — Dataset View has no bespoke codename (decision #1), so this is its permanent final state, not a stopover.
  - `catalog/integrations/views.py` → Phase 3 replaces the call with `has_dataset_perm(request.user, codename, dataset)` directly.
  - `agent/views.py` (`ConversationView.post`, `ConversationListView.post`) → Phase 4 replaces the call with `has_dataset_perm(request.user, "agent.converse", dataset)` directly.
  - `has_dataset_access()` itself is deleted once Phase 4 lands (its last caller).

- **Models & migrations** (`account`, depends on `account.0002_user_is_service_account`): `0003_dataset_role_and_assignments.py` — `CreateModel(DatasetRole)`, `CreateModel(DatasetUserRoleAssignment)`, `CreateModel(DatasetGroupRoleAssignment)`. Tables land empty — no data migration (see "Migration strategy" below).
- **`account/authorization.py`** (new) — `is_dataset_member`, `datasets_visible_to`, `has_dataset_perm` as above. Nothing calls them yet; they exist for Phase 1 onward to start using.
- `catalog`: `000X_remove_dataset_users_m2m.py` — `RemoveField(DataSet, "users")`. No backfill precedes it (see "Migration strategy").
- `DataSetUserListView`/`DataSetUserView` stubbed to no-ops (see section below) rather than re-pointed at the new tables — there's no seeded role yet for them to assign.

**Test:** migrations run clean on a fresh DB; `manage.py check` and the existing test suite pass. Expected, deliberate fallout: any existing test asserting a 403/denial for a non-member (e.g. conversation- or integration-access-denial tests) now fails, since enforcement is intentionally absent until each entity's own phase reinstates it via `has_dataset_perm`/`is_dataset_member` — that's not a Phase-0 regression to chase, it's the point of the stub. Those specific tests get updated (or deleted and rewritten) by the phase that reinstates the check they were testing.

---

### Phase 1 — Dataset permissions (CRUD, global-only; View = config + catalog access)

- `catalog/views.py`:
  - `DataSetListView.get_queryset` → `datasets_visible_to(request.user)`.
  - `DataSetListView.perform_create` → require global `catalog.add_dataset` (was: `is_staff` only).
  - `DataSetDetailView` → `permission_classes = [IsAuthenticated]` + explicit checks per method: GET → `is_dataset_member(request.user, dataset)`; PUT/PATCH → global `catalog.change_dataset`; DELETE → global `catalog.delete_dataset`. Deliberately **no** per-dataset self-service edit/delete — matches decision #1 (Dataset is global-only) and stays close to today's staff-only behavior for mutations.
  - `ConfigView`/`ConfigLanguageModelView`/`ConfigEmbeddingModelView` → `permission_classes = [IsAuthenticated]`, drop `IsAdminUser`, **and** `@any_permission_required(catalog.add_dataset, catalog.change_dataset)` on `get` (see decision #2 above) — their only caller is the New/Edit Data Set form, so a user who can do neither has no legitimate reason to see this catalog.
- `catalog/entities/views.py` (catalog browsing) → replace `has_dataset_access` (still the Phase 0 stub up to this point) with `is_dataset_member(request.user, dataset)` — this is the "access to catalog" half of View, and its permanent final state (see Phase 0).

**Test:** a user with no role assignment on a dataset can't see or touch that dataset's config or catalog; a user with a role assignment on a dataset retains access to it; a user granted global `catalog.view_dataset` sees every dataset's config/catalog regardless of role assignment; a plain role holder still cannot rename/delete their dataset (only a global `change_dataset`/`delete_dataset` grantee or admin can); a user holding neither `add_dataset` nor `change_dataset` gets 403 from all three Config views, while a holder of either one can use them.

---

### Phase 2 — Agent permissions (CRUD)

Closes baseline gap #1.

- `agent/views.py`: `AgentView.get`/`.post` and `AgentDetailsView.get`/`.put`/`.delete` — add `has_dataset_perm(request.user, "agent.view_agent"/"agent.add_agent"/"agent.change_agent"/"agent.delete_agent", dataset)`, dataset resolved from the query param (list/create) or `agent.dataset` (detail).

**Test:** a dataset outsider (no role assignment, no relevant permission) can no longer list, view, create, edit, or delete its agents (previously: zero enforcement, anyone logged in could); a role holding only `view_agent` can list/view but not mutate; a role holding full CRUD can do all four.

---

### Phase 3 — Integration permissions (CRUD + Sync)

- `catalog/0XXX_integration_sync_permission.py` — `AlterModelOptions(Integration)` adding `permissions = [("sync_integration", "Can sync this integration")]`.
- `catalog/integrations/views.py`: replace `_DataSetScopedView`'s `has_dataset_access` call (still the Phase 0 stub up to this point) with `has_dataset_perm(request.user, codename, dataset)`, one codename per action — `view_integration` (GET), `add_integration` (POST create), `change_integration` (PATCH edit), `sync_integration` (the sync-trigger action, **no longer folded into `change_integration`**), `delete_integration` (DELETE).

**Test:** a role holding CRUD but not `sync_integration` can edit an integration's config but can't trigger a sync, and vice versa; a role holding both can do both.

---

### Phase 4 — Conversation permissions (View all + Converse)

Closes baseline gaps #3, #4, #6 (conversation half).

- `agent/0031_conversation_converse_permission.py` — `AlterModelOptions(Conversation)` adding `permissions = [("converse", "Can converse with this data set's agents")]`. (`view_conversation` needs no migration — it's already a Django default.)
- `agent/views.py`:
  - `ConversationView.post` — replace `has_dataset_access` (still the Phase 0 stub up to this point — its last caller, so the stub is deleted alongside this change) with `has_dataset_perm(request.user, "agent.converse", conversation.data_set)`, **and** add `user=request.user` to the conversation lookup (closes gap #3 — flag as a deliberate bug fix, confirm it's not an intentional shared-conversation feature before shipping).
  - `ConversationListView.post` — replace `has_dataset_access` with `has_dataset_perm(request.user, "agent.converse", dataset)`.
  - `ConversationListView.get_queryset` / `ConversationView.get` — currently hard-filtered to `user=request.user` for everyone (closes gap #6, conversation half); relax so a caller holding `agent.view_conversation` (globally, or per-dataset for that dataset's conversations) sees all conversations in scope, while everyone else keeps seeing only their own.
  - `MessageFeedbackView` — add `message.conversation.user == request.user` check (closes gap #4).

**Test:** a user holding `converse` on a dataset can converse and, absent `view_conversation`, sees only their own conversation history; a global or per-dataset `view_conversation` grantee sees every conversation in scope; the co-member-posting-into-someone-else's-conversation bug is closed; `MessageFeedbackView` rejects feedback on a message from someone else's conversation.

---

### Phase 5 — Agentic Execution permissions (View all + Create)

Closes baseline gaps #2, #6 (execution half). No new permission declarations — `AgenticExecution` already carries unused Django-default `add_agenticexecution`/`view_agenticexecution`.

- `agent/agentic_execution/views.py`:
  - `StartAgenticExecutionView` — add `has_dataset_perm(request.user, "agent.add_agenticexecution", agent.dataset)` before starting an execution.
  - `AgenticExecutionListView`/`AgenticExecutionDetailView` — currently hard-filtered to `conversation__user=request.user`; relax so a caller holding `agent.view_agenticexecution` (globally, or per-dataset) sees all executions in scope, mirroring Phase 4's Conversation treatment exactly.

**Test:** a dataset outsider can't start an execution on its agents; a user holding `add_agenticexecution` on a dataset starts one and, absent `view_agenticexecution`, sees only their own past executions; a `view_agenticexecution` grantee (global or per-dataset) sees every execution in scope.

---

### Phase 6 — Users CRUD

- `account/views/users.py` — swap `IsAdminUser` for `HasPermission` with per-method `permission_required` (`GET`→`account.view_user`, `POST`→`account.add_user`, `PATCH`→`account.change_user`, `DELETE`→`account.delete_user`). `IsAdminUser` itself was already replaced by a bespoke `IsAdmin` (checks `is_superuser`, not `is_staff` — see the reversed decision above) ahead of this phase, as part of a repo-wide sweep; that swap isn't this phase's remaining scope — the fine-grained per-method codename split above still is.
- `account/serializers.py`: `AccountSerializer` — add `permissions` (`SerializerMethodField`, list of codenames the user holds globally), so the frontend has something to gate on beyond `isAdmin` once Phase 9 lands.

**Test:** a user granted only `account.view_user` can list/view users but can't create, edit, or delete them; a user with no `account.*_user` permission who also isn't an admin (`is_superuser`) gets 403 on all of `/api/users`.

---

### Phase 7 — Service Account CRUD

- `account/0009_serviceaccount_permissions.py` — `AlterModelOptions(User)` adding `permissions = [("add_serviceaccount", ...), ("change_serviceaccount", ...), ("delete_serviceaccount", ...), ("view_serviceaccount", ...)]`.
- `account/views/service_accounts.py` — swap `IsAdminUser` for `HasPermission` keyed off the new bespoke codenames (`GET`→`view_serviceaccount`, `POST`→`add_serviceaccount`, `PATCH`→`change_serviceaccount`, `DELETE`→`delete_serviceaccount`), fully independent of Phase 6's `*_user` codenames. Same note as Phase 6: `IsAdminUser` here is already `IsAdmin` post-sweep; the codename split is this phase's remaining scope.

**Test:** a user granted `account.view_user`/`change_user` (Phase 6) has **no** access to `/api/service_accounts/` unless separately granted the matching `*_serviceaccount` codenames, and vice versa — the two entities are confirmed independently grantable.

---

### Phase 8 — Permission Management (admin lockout, Groups CRUD, Dataset Roles CRUD, role assignment)

- **Self-lockout guard** (`account/authorization.py`) — block demoting (`is_superuser=False`) or deactivating (`is_active=False`) **the last remaining `is_superuser=True` user** (ports the pattern from `feature/ent-333-...`'s `assert_user_deactivatable`, retargeted from group membership to the `is_superuser` flag — see the reversed decision above; exposed to the API/frontend as `is_admin`/`isAdmin`, never as `is_superuser`). Wired into the Users/Service-Account update serializers' `validate()`.
- **"Only admin can give admin"** — flipping another user's `is_superuser` (`is_admin` on the wire) requires `request.user.is_superuser` itself; hardcoded, not a delegable permission (same reasoning as the admin-of-admin surfaces below — a "grant admin" permission would let its holder grant themselves admin).
- `account/views/groups.py` (new) — `GroupListView`/`GroupDetailView`, CRUD on `Group` + its `permissions` M2M — the note's "general" groups. `IsAdmin`.
- `account/views/dataset_roles.py` (new) — `DatasetRoleListView`/`DatasetRoleDetailView` — the note's "dataset-specific" groups. `IsAdmin`. Delete blocked while `DatasetUserRoleAssignment.objects.filter(role=role).count() + DatasetGroupRoleAssignment.objects.filter(role=role).count()` is nonzero (surface the count in the response body).
- `account/views/permissions.py` (new) — `GET /api/permissions?scope=global|dataset`, `IsAdmin`. `scope=global` returns all 23; `scope=dataset` returns the 11 dual-scope ones only.
- `account/views/dataset_access.py` (new) — assign/revoke a `DatasetRole` to a user or group on a dataset (`POST`/`DELETE` under `/api/data_sets/<id>/roles/`). **Replaces** `DataSetUserListView`/`DataSetUserView` for real — delete them now, straightforward since Phase 0 already stubbed them to no-ops and nothing has depended on them since. `IsAdmin`.
- `account/admin.py`, `catalog/admin.py`, `pecl/urls.py`: deregister `UserAdmin`/`DataSet`/`Integration`, drop the `/admin` URL include (per checklist — predates this refactor, unrelated cleanup bundled in since it's low-risk and already flagged).

**Test:** cannot demote/deactivate the last admin (`is_superuser`) user, whether acting on self or via another admin; a non-admin can never grant admin to anyone, including themselves; role-in-use delete guard fires on both `DatasetRole` and `Group`; assigning a Group a `DatasetRole` on a dataset grants its members dataset-scoped access resolved through current group membership (no per-member row materialized); `/admin` is unreachable.

---

### Phase 9 — Frontend (separate branch/PR, after all of the above)

Deliberately last and deliberately isolated — starts once Phases 0–8 are merged to `main`, so it's built against the final endpoint/permission shape instead of chasing backend changes mid-flight. Port structure/patterns from `feature/ent-333-...`'s equivalents, rewritten against the new endpoints; nothing like this exists on `main` today.

- `/roles` page, tabbed **Global Roles** (Group CRUD + members panel) / **Dataset Roles** (DatasetRole CRUD) — port `group-modal.tsx`, `group-members-panel.tsx`, dataset-role list/detail pages, `PermissionChecklist`/`CheckboxListInput`. No `implied_view_permission` concept — every checkbox is independent.
- Dataset detail → **Access** tab: replace the current plain add/remove-user table (`data-set-user-list.tsx`) with a role-assignment table (user or group → role, add/remove), calling `dataset_access.py`.
- `Account`/`User` types gain `permissions: string[]`; `lib/types.ts` `DataSet` type unchanged.
- Nav gating (`main-sidebar.tsx`, `data-set-selector.tsx`, `main.tsx` route loader, `login-form.tsx`) — keep `account.isAdmin` where it means "sees the whole admin surface" (already wired end-to-end ahead of this phase, as part of the `is_staff`→`is_superuser`/`is_admin` sweep); gate the new Roles nav item and the Users/Service Accounts nav entries on `account.permissions.includes(...)` where a finer grain now exists. Add one `hasPermission(account, codename)` helper — none exists on `main` today.

**Test:** full manual pass — create a Group with `add_dataset`, create a DatasetRole with `converse` only, verify both grant exactly what's expected and nothing more; Users, Service Accounts, Groups, Roles screens all round-trip against the new backend.

---

## Open items to confirm before/while implementing

1. `ConversationView.post`'s ownership-filter fix (Phase 4) is a behavior change — confirm it's a bug, not an intentional "any dataset member can post into any conversation in that dataset" feature.
2. Phase 1's Dataset mutation gating (`change_dataset`/`delete_dataset` global-only, no per-dataset self-service) is a direct consequence of decision #1 — confirm this matches intent, since it means an ordinary dataset "owner" can never rename or delete the dataset they were given access to, only staff or an explicit global grantee can.
3. **Whether any backward-compatible data migration is needed at all** (see "Migration strategy") — raise with the tech lead; this plan currently assumes a clean DB and seeds nothing.
4. Once no seeded role exists, **someone has to hold a role on a dataset before they can do anything with it** — until Phase 8's role-assignment UI exists, granting the very first role on a dataset needs a manual DB write or the Django admin. Worth deciding whether Phase 8 should land earlier than Phase 6/7 for exactly this reason, or whether that's acceptable for the rollout window.

---

## Appendix: the Permissions Note (source, verbatim)

```
# Permissions Note

## Dataset
- CRUD
- View - access to configuration, access to catalog

## Agent
- CRUD

## Integration
- CRUD
- Sync

## Conversation
- View - all conversations (including ones not your own)
- Converse - also gives access to your own history

## Agentic Executions
- View (all)
- Create (also gives you visibility into your own past agentic executions)

## Users
- CRUD

## Service Account
- CRUD

## Permission Management
- Only admin can give admin, or deactivate admin
- Groups (general, dataset-specific) CRUD

---

Note: All permissions are global. Agent / Integration / Conversation / Agentic Executions also have dataset-specific counterparts.
```
