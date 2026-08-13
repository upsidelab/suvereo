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
2. **Service Account gets its own CRUD codenames, separate from User**, reversing decision #3 below. There's no separate `ServiceAccount` model on `main` (confirmed — no proxy models exist anywhere in the codebase) and introducing one is out of scope here, so `add_serviceaccount`/`change_serviceaccount`/~~`delete_serviceaccount`~~/`view_serviceaccount` are declared as bespoke entries in `User.Meta.permissions`, alongside (not replacing) the Django-default `add_user`/`change_user`/`delete_user`/`view_user` the same model already carries. Same table, same model, two independently-grantable permission sets — granting one says nothing about the other. **`delete_serviceaccount` was dropped during Phase 7 implementation: three codenames, not four.** No endpoint deletes a service account, and unlike the `*_user` set — Django defaults that exist in `auth_permission` whether this plan wants them or not — these are bespoke rows this plan chooses to create. A bespoke codename that gates nothing isn't inert: it surfaces in Phase 8's `/api/permissions` listing and as a checkbox in Phase 9's role editor, so an admin can grant "Can delete service account" and get nothing for it. Adding it later, alongside the endpoint that needs it, is a one-line migration.
3. **Conversation and Agentic Execution "view all" need no new codenames.** Both models already carry an unused, Django-default `view_conversation` / `view_agenticexecution` permission (neither model sets `default_permissions = ()`). Rather than invent `view_all_conversations` from scratch, this plan repurposes those existing defaults as exactly that oversight permission — same "already exists, just put it to use" idiom the rest of this doc leans on. This reverses decision #4 below (which rejected a "view all" conversations feature outright; the note asks for it explicitly, for both entities).
4. **Integration's "Sync" is its own codename, not folded into `change_integration`.** The note lists CRUD and Sync as separate bullets under Integration. Bespoke `sync_integration`, declared in `Integration.Meta.permissions`, dual-scope like the rest of Integration's codenames.
5. **Phased, one-entity-at-a-time delivery**, chosen so each phase is testable in isolation without the next entity's work landing first — see "Phased delivery order."
6. **Holding `add`/`change`/`delete` for an entity requires also holding `view` for that same entity — validated, not implied.** Raised while discussing Phase 2 in review: if you can mutate something you should logically be able to see it. Resolved as a **backend validation rule on whichever permission set is being saved** (`DatasetRole.permissions`, `Group.permissions`, and any other place a set of codenames is granted at once) — rejecting a save that grants `add_X`/`change_X`/`delete_X` for an entity without also granting `view_X`, rather than silently auto-adding the missing `view_X`. The distinction matters: a silent auto-grant hides what was actually decided from whoever reads the stored grants later; a rejection forces the admin to explicitly check the `view_X` box themselves, so the DB only ever reflects a deliberate choice — same "informed, not automatic" reasoning as the rest of this doc's admin-of-admin guards. This reverses Phase 9's original "No `implied_view_permission` concept" line below — the *checkboxes* are still independent (nothing pre-checks itself on load), but the *save* is no longer independent per checkbox. Lands with whichever phase first builds a permission-set-editing endpoint — realistically Phase 8 (`DatasetRole`/`Group` CRUD), since nothing before it lets anyone assign an arbitrary set of codenames at once.
   - **Scope carve-outs, decided per-entity rather than applied blanket:** `agent.converse` / `agent.add_agenticexecution` already carry their own implicit *own-scoped* visibility (per the note: "Converse - also gives access to your own history", "Create - also gives you visibility into your own past agentic executions"). `agent.view_conversation` / `agent.view_agenticexecution` are the separate *view-all* oversight codename, not a prerequisite for the create/converse action — so this dependency does **not** apply to Conversation or Agentic Execution the way it does to Dataset/Agent/Integration/User/Service Account. **Resolved at the start of Phase 3 implementation: `sync_integration` does *not* require `view_integration`.** The dependency rule as decided is specifically "`add`/`change`/`delete` implies `view`" — `sync_integration` is none of those three, so it isn't in scope for the rule by its own wording, the same way `agent.converse`/`agent.add_agenticexecution` sit outside the analogous Conversation/Agentic-Execution dependency. A role holding only `sync_integration` can trigger a sync without being able to list/view integrations first; Phase 3's tests assert exactly this (`test_role_holding_only_sync_can_trigger_sync`).

### Decisions from the original draft that still stand

1. ~~**Admin flag stays `is_staff`, not `is_superuser`.**~~ **Reversed during Phase 1 implementation.** `is_superuser` is what Django actually built for "bypass every permission check": `PermissionsMixin.has_perm()` shortcuts to `True` for an active superuser *before* it ever consults `user_permissions`/`groups`. That means every helper below gets the bypass for free just by calling `has_perm(...)` — no hand-rolled `is_staff or ...` (nor `is_superuser or ...`) at any call site, which is a genuine simplification, not just a relabeling. `is_staff` reverts to Django's own native meaning (can open `/admin`) and carries zero authorization weight anywhere in this app; DRF's built-in `IsAdminUser` (which checks `is_staff`) is replaced by a bespoke `IsAdmin` (checks `is_superuser` directly) at every admin-of-admin surface that doesn't go through `has_perm`. Externally, neither Django flag is named directly: the API and frontend only ever expose `is_admin` / `isAdmin` — every serializer field is declared as `is_admin = serializers.BooleanField(source="is_superuser")`, so the wire contract doesn't hint that this is backed by Django's own `is_superuser` field (which would otherwise leak an implementation detail — e.g. "they're on Django" — to API consumers) while internal code (`validated_data`, `instance.is_superuser = ...`) keeps reading/writing the real model attribute unchanged.
2. **No `configure_models` permission** still stands — no new bespoke codename is introduced for these views. ~~`IsAuthenticated`-only~~ **partially reversed during Phase 1 implementation.** `ConfigView`/`ConfigLanguageModelView`/`ConfigEmbeddingModelView` are read-only catalogs of available provider/model names, not a mutation on any resource, and `IsAdminUser` is still dropped — but they're not left fully open to any authenticated user either: the only caller is `data-set-form.tsx` (New/Edit Data Set), so a user who can neither create nor edit a dataset has no legitimate use for this catalog and gets nothing from it. Gated on the existing `catalog.add_dataset` **or** `catalog.change_dataset` (global, any-of — see `any_global_permission_required` below), reusing Dataset's own CRUD codenames rather than inventing a new one, consistent with the rest of this doc's "already exists, just put it to use" idiom.
3. ~~**`manage_users`/`manage_service_accounts` collapse into one.**~~ **Reversed by decision #2 above** — the note treats them as separate entities, so they get separate codenames after all.
4. ~~**No `view_all_conversations`.**~~ **Reversed by decision #3 above** — the note asks for it explicitly (and its Agentic Executions twin), satisfied by repurposing the existing default `view_*` codenames rather than inventing a new one.

## Final permission set (32 codenames, no scope duplication)

*(The original "23" was a miscount — the two tables below have always listed more than that. Corrected during Phase 7 to 19 global-only + 13 dual-scope = 32, after dropping `delete_serviceaccount`.)*

Global-only (no per-dataset counterpart):

| Codename | Where declared |
|---|---|
| `catalog.add_dataset` / `change_dataset` / `delete_dataset` / `view_dataset` | already exist (Django default) |
| `account.add_user` / `change_user` / `delete_user` / `view_user` | already exist (Django default) |
| `account.add_serviceaccount` / `change_serviceaccount` / `view_serviceaccount` | **new** — bespoke, added to `User.Meta.permissions` (no `delete_` — see decision #2) |
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

Not a permission codename at all: **"only admin can give admin, or deactivate admin"** is a hardcoded `request.user.is_superuser` gate (shipped in Phase 6/7 as `OnlyAdminsManageAdminsMixin`) — deliberately not delegable, same reasoning as the admin-of-admin surfaces below. Externally this flag is never called `is_superuser`; the API/frontend name is `is_admin`/`isAdmin` (see the reversed decision above).

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

Phase 1 shipped the global-only case as a pair of method decorators rather than the permission class originally sketched here, since several call sites (e.g. `DataSetDetailView`) need a different codename per HTTP method on the same view. `global_permission_required` is the single-codename gate; `any_global_permission_required` is its any-of counterpart, needed for the Config views (see decision #2 above), which are gated on `add_dataset` **or** `change_dataset` rather than a single codename. (Named for the global-only case specifically once Phase 2 introduced a dataset-scoped sibling, `any_permission_on_any_dataset_required` — see Phase 2 below.) An `all_permissions_required` (every one of several codenames, not just one) is a natural next addition if a view ever needs it — no call site does yet, so it isn't built. Names follow Django's own `permission_required` convention (`django.contrib.auth.decorators`) deliberately — its actual *implementation* isn't reused, since it's redirect-based (wrong for an API even with `raise_exception=True`, which still collapses 401-vs-403 into a flat 403 — DRF's `self.permission_denied()` gets this right) and its multi-codename form is AND-only (`has_perms`), not the any-of semantics needed here:

```python
def global_permission_required(codename: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not self.request.user.has_perm(codename):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)
        return wrapper
    return decorator


def any_global_permission_required(*codenames: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not any(self.request.user.has_perm(codename) for codename in codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)
        return wrapper
    return decorator
```

~~`HasPermission` (the class form) may still be worth introducing in Phase 6/7 for the views that *are* uniformly one-codename-per-method — not decided yet, not blocking.~~ **Decided during Phase 6/7: no — the two decorators already cover it, so no class form is introduced.** A `HasPermission` class keyed off a per-view `permission_required` map was written and then removed: it bought only a deny-by-default for unmapped HTTP verbs, which isn't worth a second mechanism doing the same job as `global_permission_required`/`any_global_permission_required` right beside it. Phases 6/7 use the decorators throughout, exactly as Phases 1–3 do, and `account/authorization/permissions.py` keeps `IsAdmin` as its only member.

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

~~Whether a *real* backward-compatible migration path (preserving existing dataset memberships across this refactor) is ever needed is explicitly **left open**~~ — **settled with the team during Phase 7: no migration path is needed, and none will be written.** This is a major version; the data schema does not need to stay compatible with pre-refactor deployments, and no existing `DataSet.users` membership (nor the `data_set_ids` that echoed it through the service-account API) gets carried across. No backfill migration, no seeded role, nothing to preserve.

The practical consequence, actioned during Phase 7: the three `data_set_ids` stubs left behind by Phase 0 are **deleted rather than kept as placeholders** — the field is gone from `CreateUpdateServiceAccountSerializer` (create and update), from `ServiceAccountSerializer`, and from the `createadminserviceaccount` management command, along with the `# NOTE:` comments that flagged them as pending. Service accounts simply have no dataset association in the API any more; they get one back through Phase 8's role assignments if and when that's wanted. The frontend already tolerates the field's absence (`serviceAccount.dataSetIds || []` in `edit-service-account-form.tsx`), so nothing there breaks ahead of Phase 9.

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

- `agent/views.py`: `AgentView.get`/`.post` and `AgentDetailsView.get`/`.put`/`.delete` — dataset resolved from the query param (list) / request body (create) / `agent.dataset` (detail), then gated via a new `enforce_dataset_scoped_permission(view, codename, dataset)` helper (`account/authorization/helpers.py`) rather than a bare `has_dataset_perm` call: holding the codename (globally or per-dataset) passes; lacking it while still a member of the dataset denies with 403; having no relationship to the dataset at all denies with 404, so its existence is never confirmed to an outsider. `DataSetDetailView.get` (Phase 1) and `EntityRecordsView` (catalog browsing) were retrofitted to the same 404-obscuring shape for consistency, scoping their lookup through `datasets_visible_to` instead of fetch-then-403.
- `AgentTypesView` (`/api/agents/types`) — was fully unguarded (`IsAuthenticated` only); gated on `any_permission_on_any_dataset_required(agent.add_agent, agent.change_agent)`, a new dual-scope sibling of `any_global_permission_required` (passes on a *global* grant of either codename, or a *per-dataset* grant on any single dataset — unlike Dataset's Config views, there's no one dataset to scope a global-only check to). Backing helper: `has_any_permission_on_any_dataset(user, *codenames)`. `EntityListView` (catalog browsing) had the identical unguarded gap, closed the same way via a presence-only sibling, `has_any_dataset_access(user)`.

**Test:** a dataset outsider (no role assignment, no relevant permission) gets 404 listing/viewing/creating/editing/deleting its agents (previously: zero enforcement, anyone logged in could); a dataset member with no `agent.*` permission gets 403; a role holding only `view_agent` can list/view but not mutate; a role holding full CRUD can do all four; a user with `add_agent` on one dataset (no global grant) can still load `/api/agents/types`.

---

### Phase 3 — Integration permissions (CRUD + Sync)

- `catalog/0XXX_integration_sync_permission.py` — `AlterModelOptions(Integration)` adding `permissions = [("sync_integration", "Can sync this integration")]`.
- `catalog/integrations/views.py`: replace `_DataSetScopedView`'s `has_dataset_access` call (still the Phase 0 stub up to this point) with `has_dataset_perm(request.user, codename, dataset)`, one codename per action — `view_integration` (GET), `add_integration` (POST create), `change_integration` (PATCH edit), `sync_integration` (the sync-trigger action, **no longer folded into `change_integration`**), `delete_integration` (DELETE).
- `IntegrationTypeListView` (`/api/integration-types`) — was fully unguarded (`IsAuthenticated` only), the same gap `AgentTypesView` had before Phase 2; closed the same way, via `@any_permission_on_any_dataset_required(catalog.add_integration, catalog.change_integration)`.

**Test:** a role holding CRUD but not `sync_integration` can edit an integration's config but can't trigger a sync, and vice versa; a role holding both can do both; a user with no `add_integration`/`change_integration` anywhere gets 403 from `/api/integration-types`, while a per-dataset grant of either one (no global grant) is allowed through.

---

### Phase 4 — Conversation permissions (View all + Converse)

Closes baseline gaps #3, #4, #6 (conversation half).

- `agent/0031_conversation_converse_permission.py` — `AlterModelOptions(Conversation)` adding `permissions = [("converse", "Can converse with this data set's agents")]`. (`view_conversation` needs no migration — it's already a Django default.)
- `account/authorization/helpers.py` — new `datasets_with_permission(user, codename)`, a `datasets_visible_to`-shaped sibling: globally the codename holder gets every dataset (superusers included, for free via `has_perm`), otherwise only the datasets with a matching per-dataset role assignment. `ConversationListView.get_queryset` / `ConversationView.get` OR this into the owner-only queryset rather than branching on the global-grant case explicitly. Reused as-is by Phase 5 for `AgenticExecution`'s identical "view all" shape.
- `agent/views.py`:
  - `ConversationView.post` — replace `has_dataset_access` (still the Phase 0 stub up to this point — its last caller, so the stub is deleted alongside this change, along with the now-stale comment in `agent/core/repositories.py` referencing it) with `has_dataset_perm(request.user, "agent.converse", conversation.data_set)`, **and** add `user=request.user` to the conversation lookup (closes gap #3). **Resolved: this is a deliberate bug fix, and it applies universally — including to admins** (see "Open items to confirm" #1). `test_admin_can_post_to_any_conversation` was split into `test_admin_cannot_post_to_conversation_they_do_not_own` (404) and `test_admin_can_post_to_own_conversation_without_converse_permission` (202 — the *permission* check still bypasses for superusers, only ownership doesn't).
  - `ConversationListView.post` — replace `has_dataset_access` with `enforce_dataset_scoped_permission(self, "agent.converse", agent.dataset, obscured_model=Agent)`, checked **before** `ConversationManager.create_conversation` runs (caught in review — the original ordering created the row first and only checked access afterward, so a denied request still left an orphan `Conversation` behind). The agent is resolved via `get_object_or_404(Agent, ...)` (which already 404s soft-deleted agents via the default manager) so the dataset is known before any write happens. This is the same shape as `AgentView.post` in Phase 2 — dataset resolved from a caller-supplied id with no proven prior relationship — so it gets the same 404-obscuring treatment; the earlier `raise NotFound("Agent not found.")` was swapped for `get_object_or_404` specifically so the two 404s share a response body (`"No Agent matches the given query."`) and stay indistinguishable, asserted by `test_create_conversation_outsider_gets_identical_404_body_to_a_nonexistent_agent`.
  - `ConversationListView.get_queryset` / `ConversationView.get` — currently hard-filtered to `user=request.user` for everyone (closes gap #6, conversation half); relax so a caller holding `agent.view_conversation` (globally, or per-dataset for that dataset's conversations) sees all conversations in scope, while everyone else keeps seeing only their own.
  - `MessageFeedbackView` — closes gap #4 by owner-scoping the lookup itself (`get_object_or_404(Message, id=id, conversation__user=request.user)`) rather than fetch-then-compare, so a non-owner and a nonexistent message id are indistinguishable (both `404 {"detail": "No Message matches the given query."}`). Same ownership-is-a-data-boundary treatment as `ConversationView.post` — no admin bypass. This also retires the endpoint's bespoke `{"error": ...}` body, which was the only place in the app using `error` instead of `detail`.
  - `ConversationFileUploadView.post` (`agent/views.py`, file upload onto an *existing* conversation) — caught in review: it already scoped its lookup to `user=request.user`, but never checked `converse` at all, so an owner whose `converse` grant on that dataset had since been revoked could still attach files. Added `has_dataset_perm(request.user, "agent.converse", conversation.data_set)` right after the ownership fetch, same shape as `ConversationView.post`. (File upload never creates a conversation itself — `process_file_upload_task` only attaches a `ConversationFile` to a `conversation_id` that must already exist; the only conversation-creation call site remains `ConversationListView.post`.)

**Why `ConversationView.post`/`ConversationFileUploadView.post` deny with a bare `self.permission_denied(...)` (403) instead of `enforce_dataset_scoped_permission` (404-obscuring), unlike every other dual-scope call site** — raised in review, since Phases 2–3 route every denial through the helper. Both endpoints fetch owner-scoped first (`get_object_or_404(Conversation, ..., user=request.user)`), so by the time the permission check runs the caller has *proven* they own a conversation on that dataset — its existence is already legitimately disclosed to them, and there's nothing left to obscure. Applying the helper here would 404 an owner who holds no role on the dataset (a revoked grant, say) while `ConversationView.get` still returns 200 for that very conversation; GET 200 / POST 404 on one resource is incoherent, whereas 403 reads correctly as "you can see it, you can't converse in it". The *body* was still brought in line — the original hand-rolled `{"detail": "No dataset access."}` was a second 403 dialect and is now DRF's standard `permission_denied` response, matching every other denial in the refactor. `ConversationListView.post` gets the helper because it's the opposite case: no ownership is established before the check, so the 404 obscuring is load-bearing there.

**Test:** a user holding `converse` on a dataset can converse and, absent `view_conversation`, sees only their own conversation history; a global or per-dataset `view_conversation` grantee sees every conversation in scope; the co-member-posting-into-someone-else's-conversation bug is closed for everyone, admins included; an admin can still post into a conversation they *do* own without holding `converse` anywhere; `MessageFeedbackView` rejects feedback on a message from someone else's conversation, admins included; a denied `ConversationListView.post` leaves no `Conversation` row behind; a conversation owner without `converse` on its dataset gets 403 from `ConversationFileUploadView` same as from `ConversationView.post`; a dataset outsider gets 404 from `ConversationListView.post` with a body identical to a nonexistent agent's, while a dataset *member* lacking `converse` gets 403 there; a non-owner gets 404 from `MessageFeedbackView` with a body identical to a nonexistent message's.

---

### Phase 5 — Agentic Execution permissions (View all + Create)

Closes baseline gaps #2, #6 (execution half). No new permission declarations — `AgenticExecution` already carries unused Django-default `add_agenticexecution`/`view_agenticexecution`.

- `agent/agentic_execution/views.py`:
  - `StartAgenticExecutionView` — ~~add `has_dataset_perm(request.user, "agent.add_agenticexecution", agent.dataset)`~~ **implemented as `enforce_dataset_scoped_permission(self, PERMISSIONS.AGENTIC_EXECUTION.CREATE, agent.dataset, obscured_model=Agent)`** before starting an execution. The bare `has_dataset_perm` wording predates Phase 2's helper; this endpoint is exactly the shape Phase 4 called out for `ConversationListView.post` — a dataset resolved from a caller-supplied agent id with no proven prior relationship — so it gets the same 404-obscuring treatment rather than a flat 403. The hand-rolled `try/except Agent.DoesNotExist` → `{"detail": "Agent not found."}` was swapped for `get_object_or_404(Agent, ...)` for the same reason Phase 4 swapped `ConversationListView.post`'s `raise NotFound(...)`: so the outsider 404 and the nonexistent-agent 404 share a response body (`"No Agent matches the given query."`) and stay indistinguishable, asserted by `test_outsider_gets_identical_404_body_to_a_nonexistent_agent`. (Soft-deleted agents still 404 — `Agent`'s default manager already excludes them.)
  - `AgenticExecutionDefinitionTypesView` (`/api/agents/<id>/agentic-execution-definitions/`) — **not in this phase's original scope; added during implementation.** It was fully unguarded (`IsAuthenticated` only) and takes an `agent_id`, so any logged-in user could confirm an arbitrary agent's existence and read the execution catalog for a dataset they have no relationship to — the same gap `AgentTypesView` (Phase 2) and `IntegrationTypeListView` (Phase 3) had, and it belongs to this entity. Closed with the same `enforce_dataset_scoped_permission(..., CREATE, ..., obscured_model=Agent)` call as `StartAgenticExecutionView` rather than an `any_permission_on_any_dataset_required` decorator: unlike those two type-listing views there *is* one specific dataset to scope to here. Gated on `CREATE` alone (not `CREATE`-or-`VIEW_ALL`) following decision #2's Config-views reasoning — its only caller is `create-execution-modal.tsx`, so a caller who can't start an execution has no use for the catalog; a `VIEW_ALL` oversight holder reads past executions and never opens that form.
  - `AgenticExecutionListView`/`AgenticExecutionDetailView` — currently hard-filtered to `conversation__user=request.user`; relax so a caller holding `agent.view_agenticexecution` (globally, or per-dataset) sees all executions in scope, mirroring Phase 4's Conversation treatment exactly. Implemented as a shared module-level `_visible_to(user) -> Q` (`Q(conversation__user=user) | Q(agent__dataset__in=datasets_with_permission(user, VIEW_ALL))`) since both views need the identical filter. Scoped through `agent__dataset` rather than `conversation__data_set` — the two are always equal (`AgenticExecutionService.start` sets `data_set=agent.dataset` on the conversation it creates), and `agent__dataset` is the same relation `StartAgenticExecutionView` enforces against, so read and write scope can't drift.

**Test:** a dataset outsider can't start an execution on its agents; a user holding `add_agenticexecution` on a dataset starts one and, absent `view_agenticexecution`, sees only their own past executions; a `view_agenticexecution` grantee (global or per-dataset) sees every execution in scope. Added during implementation: a dataset *member* lacking `add_agenticexecution` gets 403 (not 404) from both the start and definitions endpoints, while an outsider gets 404 from both with a body identical to a nonexistent agent's; a `view_agenticexecution`-only holder is refused at the start endpoint; a per-dataset `view_agenticexecution` grant on one dataset gives no visibility into another's executions.

---

### Phase 6 — Users CRUD

- `account/views/users.py` — ~~swap `IsAdminUser` for `HasPermission` with per-method `permission_required`~~ **drop `IsAdmin` to `permission_classes = [IsAuthenticated]` and gate per method with `global_permission_required`**, the same shape Phase 1 used on `DataSetListView`/`DataSetDetailView` (`GET`→`account.view_user`, `POST`→`account.add_user`, `PUT`/`PATCH`→`account.change_user`, ~~`DELETE`→`account.delete_user`~~). `IsAdminUser` itself was already replaced by a bespoke `IsAdmin` (checks `is_superuser`, not `is_staff` — see the reversed decision above) ahead of this phase, as part of a repo-wide sweep; that swap isn't this phase's remaining scope — the fine-grained per-method codename split above still is.
  - **Reads are decorated on the HTTP handler, writes on the `perform_*` hook** — `@global_permission_required(VIEW)` on `get`, `@global_permission_required(ADD)` on `perform_create`, `@global_permission_required(CHANGE)` on `perform_update` — copying `DataSetListView` line for line. Decorating `perform_update` (rather than `put` and `patch` separately) covers both verbs in one place, since `UpdateAPIView` routes both through it. Inherited consequence of the `perform_*` placement, already true of Phase 1's `perform_create`: a caller lacking the codename who also sends an invalid body gets 400 (validation) instead of 403, because DRF validates before calling the hook. Nothing is written before the check either way.
  - **`DELETE` is deliberately ungated: no user-deletion endpoint exists** (confirmed across `account/urls.py` and the frontend's `users.ts` — users are deactivated via `is_active`, never deleted). So `account.delete_user` stays a grantable codename with nothing yet to gate; a one-line comment in `users.py` records why. **It stays only because Django creates it regardless** — Phase 7's bespoke `delete_serviceaccount`, which this plan would have had to declare deliberately, was dropped for exactly this reason (see decision #2). Whether to also suppress the unused `delete_user` row via `default_permissions` is out of scope: the plan's standing choice is to leave Django's defaults alone everywhere.
  - `UserPasswordView` (`PUT /api/users/<id>/password`) wasn't named in this phase's scope but carried the same `IsAdmin` gate; gated on `change_user`, since setting someone's password is a change to that user.
- `account/serializers.py`: `AccountSerializer` — add `permissions` (`SerializerMethodField`, list of codenames the user holds globally), so the frontend has something to gate on beyond `isAdmin` once Phase 9 lands. Implemented as `sorted(user.get_all_permissions())`, which folds in group-granted codenames and returns *every* codename for an admin (it short-circuits for superusers exactly like `has_perm`). Per-dataset role grants are deliberately **excluded** — a dataset-scoped codename means nothing without the dataset it was granted on, so it can't be flattened into this list; Phase 9's `hasPermission(account, codename)` helper is therefore a global-only check, and any per-dataset UI gating needs its own endpoint.

**Test:** a user granted only `account.view_user` can list/view users but can't create, edit, or delete them; a user with no `account.*_user` permission who also isn't an admin (`is_superuser`) gets 403 on all of `/api/users`. Added during implementation: `add_user` alone permits creation but **not** listing (the converse split, so the map is proven per-method rather than per-view); a codename granted via a `Group` is honoured; and for `AccountSerializer.permissions` — empty for a bare user, populated from direct and group grants, every codename for an admin, and unaffected by a per-dataset role assignment.

---

### Phase 7 — Service Account CRUD

- ~~`account/0009_serviceaccount_permissions.py`~~ **`account/0004_serviceaccount_permissions.py`** (the plan's number predates the real migration tree; `0003_dataset_role_and_assignments` is Phase 0's) — `AlterModelOptions(User)` adding `permissions = [("add_serviceaccount", ...), ("change_serviceaccount", ...), ("view_serviceaccount", ...)]` — three, not four; `delete_serviceaccount` is dropped (decision #2). The model-side `Meta` **must** be declared as `class Meta(AbstractUser.Meta)`, not a bare `class Meta`: `User` currently declares no `Meta` at all and therefore already inherits `AbstractUser.Meta`'s `verbose_name`/`verbose_name_plural`, which migration `0001_initial` recorded. A bare `Meta` would silently drop both and make the migration a rename as well as a permission add.
- `account/views/service_accounts.py` — ~~swap `IsAdminUser` for `HasPermission`~~ **same `IsAuthenticated` + `global_permission_required` treatment as Phase 6**, keyed off the new bespoke codenames (`GET`→`view_serviceaccount`, `POST`→`add_serviceaccount`, `PATCH`→`change_serviceaccount`; ~~`DELETE`→`delete_serviceaccount`~~ — no deletion endpoint exists, and unlike Phase 6 the codename isn't declared at all), fully independent of Phase 6's `*_user` codenames. Every handler here is already an explicit method, so all four decorate the HTTP verb directly — no `perform_*` hooks involved. Same note as Phase 6: `IsAdminUser` here is already `IsAdmin` post-sweep; the codename split is this phase's remaining scope.
  - Two endpoints beyond the CRUD four, neither named in this phase's original scope, both previously `IsAdmin`: **`ResetTokenView`** (`POST .../reset_token`) → `change_serviceaccount`, since revoking and reissuing a token mutates the account. **`CheckServiceNameView`** (`POST .../check_name`) → `@any_global_permission_required(add_serviceaccount, change_serviceaccount)`, its first use outside Phase 1's Config views: it mutates nothing and backs the name field on *both* the new and the edit form (`check-service-name-availability.tsx`), so gating it on either codename alone would break one of the two forms. Same "who legitimately needs this" reasoning as decision #2.
- **After this phase `IsAdmin` has no call sites left** — Phases 6/7 removed its last two. It stays exported, unused, until Phase 8 reintroduces it on the admin-of-admin surfaces (Groups/DatasetRoles CRUD, permission listing, dataset access). Not dead code to prune.

**Test:** a user granted `account.view_user`/`change_user` (Phase 6) has **no** access to `/api/service_accounts/` unless separately granted the matching `*_serviceaccount` codenames, and vice versa — the two entities are confirmed independently grantable. Implemented as a dedicated `TestUserAndServiceAccountPermissionsAreIndependent` class holding a full-`*_user` grantee and a full-`*_serviceaccount` grantee, asserting each is 403 across the other's endpoints while still working on its own. Also added: `view_serviceaccount` alone permits neither update, token reset, nor name check; either of `add_serviceaccount`/`change_serviceaccount` alone permits the name check.

### Pre-existing API bugs fixed alongside Phases 6/7

Found during Postman testing of the endpoints these phases touch. None were caused by the permissions work; all three are in the same two files, so they land here rather than as a separate PR.

- **Update responses echoed stale data.** `perform_update` called `self.get_object()` a second time and mutated *that* copy, while the serializer still held the instance DRF fetched in `update()` — so the DB was written correctly but the response rendered the pre-update values. Fixed by moving the mutation into the serializers' `update()` and reducing the hooks to `serializer.save()`. Same root cause made `UserSerializer` create omit `id`: `perform_create` called `create_user()` without ever calling `save()`, leaving `serializer.instance` as `None`.
- **`PATCH` was not partial.** Both update serializers indexed `validated_data["..."]` directly, so a partial body raised `KeyError` → 500. Now they iterate `validated_data.items()`, which touches only what was sent. `PUT` still requires every field (DRF applies `required` when `partial=False`), which is the correct split.
- **The service-account create response leaked `is_superuser`**, because it returned `serializer.validated_data` (keyed by `source`) instead of `serializer.data`. That contradicted the reversed decision above, which says the wire only ever says `is_admin`. Switching to `serializer.data` fixes it and adds `id`; it also drops `name` from that response, since the field is `write_only` — the only consumer destructures `{ token }`, so nothing breaks.

- **A duplicate service-account name was a 500.** Create never consulted `check_name` (a separate endpoint the UI calls first), so a colliding name reached the unique constraint on `email` and raised `IntegrityError`. Now a `validate_name` on `CreateUpdateServiceAccountSerializer` rejects it with a 400 naming the `name` field, reusing `ServiceAccountNameService.is_service_account_name_available` — which gained an optional `exclude_user` so a rename that keeps the account's own name isn't flagged as colliding with itself.

`id` is now returned by every create and update response across both entities (including the password endpoint, whose body was previously `{}`).

**Still open, same defect class, not fixed here:** `POST /api/users` and `PATCH /api/users/<id>` raise `IntegrityError` → 500 on a duplicate email, since `UserSerializer`/`UserUpdateSerializer` are plain `Serializer`s and carry no uniqueness validator. The fix mirrors the above — a `validate_email` excluding `self.instance` — but it wasn't in scope for this pass.

---

### ~~Known gap between Phase 6/7 and Phase 8~~ — CLOSED: admin-of-admin guard pulled forward into Phase 6/7

Surfaced while implementing Phase 6, then **confirmed in manual testing** (an admin user was successfully created while logged in as a non-admin) and fixed in the same PR rather than waiting for Phase 8. `UserSerializer`/`UserUpdateSerializer` both expose `is_admin` (`source="is_superuser"`), so a holder of `account.change_user` could `PATCH` themselves to `is_admin: true` and a holder of `account.add_user` could create a fresh admin — either codename was transitively equivalent to full admin. The escalation path was **new**, introduced by the `IsAdmin`→codename split.

Closed by `OnlyAdminsManageAdminsMixin` (`account/serializers.py`), mixed into `UserSerializer`, `UserUpdateSerializer`, `UserUpdatePasswordSerializer`, and `CreateUpdateServiceAccountSerializer`. Two rules, both keyed off `request.user.is_superuser` directly — never a codename, since a grantable "may grant admin" permission would let its holder grant it to themselves:

1. **A non-admin cannot set `is_admin: true`**, on create or update. Covers "create an admin" and "give admin to someone" (including to themselves).
2. **A non-admin cannot write to an account that is already an admin**, in any way. Covers "revoke admin" and "deactivate an admin" as asked — and deliberately goes further to cover *any* field, because changing an admin's email or resetting their password hands over the account just as effectively as flipping the flag. Two takeover vectors that the literal rule-list would have left open.

Denials are `403` (`rest_framework.exceptions.PermissionDenied` raised from `validate()`), not `400` — the request is well-formed, the caller simply isn't allowed to make it, which matches every other denial in this refactor.

Beyond the serializers, one view-level equivalent: **`ResetTokenView`** refuses a non-admin rotating an *admin service account's* token, since the endpoint hands the caller a working credential for that account. Not reachable through a serializer, so guarded in the view.

`self.context.get("request")` is checked rather than indexed, so a serializer used with no request — the `createadminserviceaccount` management command, which is how the very first admin gets created — bypasses the guard. Shell access is already privileged; that path stays open by design and is covered by a test.

### The last-admin lockout guard is deliberately NOT implemented — dropped, do not reintroduce

It was built during this phase (`ProtectsLastAdminMixin`, refusing any write that would leave zero active admins) and then **removed after review**. Recorded here because Phase 8's original scope asks for it, and the next person to read that bullet should know it was considered and rejected on purpose rather than forgotten:

- **No stated requirement asks for it.** The Permissions Note says *"Only admin can give admin, or deactivate admin"* — that's the escalation guard above, which stays. The lockout guard came from this plan porting `assert_user_deactivatable` out of the abandoned `feature/ent-333-...` branch. Inherited scope, not a requirement.
- **It cannot be an invariant, only an endpoint guard.** It covered two DRF endpoints; the Django admin, the shell, `createsuperuser`, and a direct `UPDATE` all bypass it. A class named for a system property it can't actually hold is worse than no class — the next reader assumes "an active admin always exists" and builds on a guarantee that isn't there.
- **It protects nothing security-relevant.** The escalation guard stops an untrusted caller *gaining* privilege. This one stopped a trusted admin doing something legal, deliberate and recoverable to themselves. No attacker benefits from an admin locking themselves out, so removing it costs the threat model nothing.
- **Recovery is cheap for this audience.** Anyone who can deploy Enthusiast can restore an admin from the shell or with a one-row DB update. The cost of the mistake is minutes, and only for someone who took a deliberate action.
- It also blocked a legitimate workflow: demoting yourself to check what a non-admin sees while testing this very refactor.

The trade being accepted: in a hosted/multi-tenant deployment — where whoever clicks "deactivate" is not whoever holds the shell — this becomes a support escalation instead of a self-service fix. If Enthusiast is ever run that way, revisit; until then it's theoretical. The cheaper mitigation is documenting the recovery command, not guarding the endpoint.

---

### Phase 8 — Permission Management (Groups CRUD, Dataset Roles CRUD, role assignment)

- ~~**Self-lockout guard**~~ **Dropped — will not be implemented.** Built during Phase 6/7 and removed after review; see "The last-admin lockout guard is deliberately NOT implemented" above for the reasoning. Original scope, for reference: block demoting (`is_superuser=False`) or deactivating (`is_active=False`) **the last remaining `is_superuser=True` user** (ports the pattern from `feature/ent-333-...`'s `assert_user_deactivatable`, retargeted from group membership to the `is_superuser` flag — see the reversed decision above; exposed to the API/frontend as `is_admin`/`isAdmin`, never as `is_superuser`). Wired into the Users/Service-Account update serializers' `validate()`.
- ~~**"Only admin can give admin"**~~ **Already landed — pulled forward into Phase 6/7** (see the closed-gap section above). Nothing left to do here; with the self-lockout guard dropped, this phase's admin-protection scope is fully discharged.
- `account/views/groups.py` (new) — `GroupListView`/`GroupDetailView`, CRUD on `Group` + its `permissions` M2M — the note's "general" groups. `IsAdmin`.
- `account/views/dataset_roles.py` (new) — `DatasetRoleListView`/`DatasetRoleDetailView` — the note's "dataset-specific" groups. `IsAdmin`. Delete blocked while `DatasetUserRoleAssignment.objects.filter(role=role).count() + DatasetGroupRoleAssignment.objects.filter(role=role).count()` is nonzero (surface the count in the response body).
- `account/views/permissions.py` (new) — `GET /api/permissions?scope=global|dataset`, `IsAdmin`. `scope=global` returns all 32; `scope=dataset` returns the 13 dual-scope ones only. (Counts corrected during Phase 7 — see "Final permission set".)
- `account/views/dataset_access.py` (new) — assign/revoke a `DatasetRole` to a user or group on a dataset (`POST`/`DELETE` under `/api/data_sets/<id>/roles/`). **Replaces** `DataSetUserListView`/`DataSetUserView` for real — delete them now, straightforward since Phase 0 already stubbed them to no-ops and nothing has depended on them since. `IsAdmin`.
- **View-dependency validation** (decision #6 above) — `DatasetRole` and `Group` serializers reject a save whose `permissions` set includes `add_X`/`change_X`/`delete_X` for an entity without the matching `view_X`, for every entity the dependency applies to (carve-outs: Conversation, Agentic Execution, and — pending Phase 3's decision — possibly Integration's `sync_integration`). The error names the specific missing `view_X` codename; nothing is auto-added on the backend's behalf.
- `account/admin.py`, `catalog/admin.py`, `pecl/urls.py`: deregister `UserAdmin`/`DataSet`/`Integration`, drop the `/admin` URL include (per checklist — predates this refactor, unrelated cleanup bundled in since it's low-risk and already flagged).

**Test:** ~~cannot demote/deactivate the last admin (`is_superuser`) user, whether acting on self or via another admin;~~ (dropped — see above) ~~a non-admin can never grant admin to anyone, including themselves;~~ (already covered by Phase 6/7's tests) role-in-use delete guard fires on both `DatasetRole` and `Group`; assigning a Group a `DatasetRole` on a dataset grants its members dataset-scoped access resolved through current group membership (no per-member row materialized); `/admin` is unreachable; saving a `DatasetRole`/`Group` with `change_agent` but not `view_agent` is rejected with a clear per-codename error, while the same set plus `view_agent` saves cleanly; saving `converse` alone (no `view_conversation`) is **not** rejected.

---

### Phase 9 — Frontend (separate branch/PR, after all of the above)

Deliberately last and deliberately isolated — starts once Phases 0–8 are merged to `main`, so it's built against the final endpoint/permission shape instead of chasing backend changes mid-flight. Port structure/patterns from `feature/ent-333-...`'s equivalents, rewritten against the new endpoints; nothing like this exists on `main` today.

- `/roles` page, tabbed **Global Roles** (Group CRUD + members panel) / **Dataset Roles** (DatasetRole CRUD) — port `group-modal.tsx`, `group-members-panel.tsx`, dataset-role list/detail pages, `PermissionChecklist`/`CheckboxListInput`. Every checkbox still starts independent — nothing pre-checks or auto-checks `view_X` on the client. Submitting a set that fails the backend's view-dependency validation (decision #6) surfaces that error inline against the relevant permission group, naming exactly which `view_X` is missing, so the admin checks it themselves rather than having it silently added.
- Dataset detail → **Access** tab: replace the current plain add/remove-user table (`data-set-user-list.tsx`) with a role-assignment table (user or group → role, add/remove), calling `dataset_access.py`.
- `Account`/`User` types gain `permissions: string[]`; `lib/types.ts` `DataSet` type unchanged.
- Nav gating (`main-sidebar.tsx`, `data-set-selector.tsx`, `main.tsx` route loader, `login-form.tsx`) — keep `account.isAdmin` where it means "sees the whole admin surface" (already wired end-to-end ahead of this phase, as part of the `is_staff`→`is_superuser`/`is_admin` sweep); gate the new Roles nav item and the Users/Service Accounts nav entries on `account.permissions.includes(...)` where a finer grain now exists. Add one `hasPermission(account, codename)` helper — none exists on `main` today.

**Test:** full manual pass — create a Group with `add_dataset`, create a DatasetRole with `converse` only, verify both grant exactly what's expected and nothing more; Users, Service Accounts, Groups, Roles screens all round-trip against the new backend.

---

## Open items to confirm before/while implementing

1. ~~`ConversationView.post`'s ownership-filter fix (Phase 4) is a behavior change — confirm it's a bug, not an intentional "any dataset member can post into any conversation in that dataset" feature.~~ **Resolved during Phase 4 implementation: it's a bug, and the fix applies universally, including to admins.** Conversation ownership is a data boundary, not a permission check — `is_superuser`'s blanket `has_perm(...)` bypass doesn't extend to it. `test_admin_can_post_to_any_conversation` (which relied on the old unscoped lookup) was replaced by `test_admin_cannot_post_to_conversation_they_do_not_own` (expects 404, same obscuring treatment as any other non-owner) and `test_admin_can_post_to_own_conversation_without_converse_permission` (admin still bypasses the *converse permission* check for free on a conversation they do own). Same reasoning applied to `MessageFeedbackView`.
2. Phase 1's Dataset mutation gating (`change_dataset`/`delete_dataset` global-only, no per-dataset self-service) is a direct consequence of decision #1 — confirm this matches intent, since it means an ordinary dataset "owner" can never rename or delete the dataset they were given access to, only staff or an explicit global grantee can.
3. ~~**Whether any backward-compatible data migration is needed at all** (see "Migration strategy") — raise with the tech lead; this plan currently assumes a clean DB and seeds nothing.~~ **Resolved with the team during Phase 7: no migration is needed.** Clean DB, nothing preserved, `data_set_ids` dropped outright rather than stubbed — see "Migration strategy".
4. Once no seeded role exists, **someone has to hold a role on a dataset before they can do anything with it** — until Phase 8's role-assignment UI exists, granting the very first role on a dataset needs a manual DB write or the Django admin. Worth deciding whether Phase 8 should land earlier than Phase 6/7 for exactly this reason, or whether that's acceptable for the rollout window.
5. ~~Whether `catalog.sync_integration` requires `catalog.view_integration`~~ **Resolved during Phase 3 implementation — no.** See decision #6's carve-out list above.
5. **Whether `catalog.sync_integration` requires `catalog.view_integration`** under decision #6's add/change/delete-requires-view validation — decide at the start of Phase 3, before `Integration`'s codenames are wired up to any role-editing UI.

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
