---
name: test-feature
description: "Testing requirements for new server features: unit tests for logic, endpoint tests covering permissions (allowed, forbidden, unauthenticated, per role), fixtures from server/conftest.py, model-bakery for data. Use when adding or changing a backend feature, endpoint, permission or model, or when asked to write or review tests."
---

# Test a feature

Backend tests use pytest-django with model-bakery. Run them from `server/`; they need Postgres with pgvector (see `sample.test.env`). Settings module is `pecl.settings` (`pytest.ini`).

```
pytest                                                   # everything
pytest agent/tests/test_views.py                         # one file
pytest agent/tests/test_views.py::TestClass::test_name   # one test
```

A feature is done when its tests pass and cover the layers below. Run `ruff check .` and `ruff format .` on the new tests.

## What to cover

**Logic.** Unit-test services, tools, retrievers, validators and model methods directly, without HTTP. Mock only boundaries (LLMs, external APIs, the injector); use real database rows through model-bakery for everything else.

**Every new or changed endpoint.** Test the response for each caller, because authorization is the part that silently regresses:
- **Unauthenticated** → `401` (use a bare `APIClient()`).
- **Authenticated without the permission** → `403`.
- **Holder of the required permission** → success status and the expected body.
- **Admin** (`admin_api_client`) → success.
- **A near-miss permission** (a different code on the same entity, e.g. `ASSIGN` where `VIEW` is required) → `403`. This proves the endpoint checks the right code.
- For data-set-scoped resources: a member via a direct role, a member via a group role, a global-permission holder, and an outsider. A non-member gets `404` where the endpoint hides the existence of the data set (see `catalog/entities/tests/test_views.py`), `403` otherwise; assert whichever the endpoint documents.
- Write endpoints: each verb separately (`post`, `patch`, `put`, `delete`), each with its own permission code; `pytest.mark.parametrize` keeps this compact.
- Validation errors, and not-found for ids that do not exist or belong to another data set.

**Permission changes.** A new permission code goes into `account/authorization/permission_codenames.py` and the rules, and its public form is published to the frontend, so `account/tests/public_permission_codes_contract.py` must be updated deliberately in the same change. A failure in `test_public_permission_codes_contract.py` means the wire format moved.

**Migrations.** A model change ships with its migration. Test data migrations on their own; generated schema migrations need no test.

## Fixtures and helpers

From `server/conftest.py`: `user`, `admin_user`, `api_client` (authenticated as `user`), `admin_api_client`, `data_set`, `conversation`, and the autouse `temp_media_root`.

From `account/tests/helpers.py` (take `PERMISSIONS` members, not public codes):
- `grant(user, PERMISSIONS.X.Y, ...)` — global permissions, via a global role (permissions only reach accounts through roles; never write `user.user_permissions`).
- `make_role(name, *codes)` and `assign_role(user_or_group, data_set, role)` — data-set-scoped permissions.
- `make_global_role`, `join_global_role`, `make_group`, `join_group` — group-based assignment.
- `client_for(user)` — an authenticated `APIClient`.

`grant`, `join_group` and friends reset Django's per-instance permission cache; after granting something to a user that already made a request, grant through these helpers, not by hand.

Create data with `baker.make(Model, ...)`; specify only the fields the test depends on.

## Conventions

- `pytestmark = pytest.mark.django_db` at the top of any module that touches the database.
- Tests sit next to the code in `<app>/tests/` (or a sub-package's `tests/`); one module per resource, e.g. `account/tests/test_views/test_groups.py`.
- Group tests in classes named for the behaviour (`TestWritingGroupsNeedsItsOwnLifecycleCode`) and name tests as sentences stating the outcome (`test_group_assign_alone_does_not_substitute_for_group_view`).
- Arrange, act, assert, separated by blank lines; assert status codes with `rest_framework.status` constants.
- Use `reverse(...)` with URL names, not hard-coded paths.
- Comments only for a non-obvious reason (as in the 404-versus-403 note); no docstrings on tests.

## Reference implementations

- Global-permission endpoint: `account/tests/test_views/test_groups.py`
- Data-set-scoped endpoint: `catalog/entities/tests/test_views.py`, `agent/tests/test_views.py`
- Permission helpers: `account/tests/helpers.py`

## Plugin code

Plugins under `plugins/` keep their tests in their own `tests/` directory, mocking the LLM and the injector (see `plugins/enthusiast-integration-mcp/tests/`). `enthusiast-common` tests run from the server's environment: `cd server && poetry run pytest ../plugins/enthusiast-common/tests`.
