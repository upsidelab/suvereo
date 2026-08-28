import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured

from account.authorization import (
    DATASET_SCOPE_PERMISSIONS,
    GLOBAL_SCOPE_PERMISSIONS,
    INTERNAL_CODES,
    PERMISSION_DEPENDENCIES,
    PERMISSION_ENTITIES,
    PERMISSIONS,
    PUBLIC_CODES,
    dependencies_within,
    entity_label,
)
from account.authorization.permission_rules import build_transitive_dependencies


class TestPermissionVocabulary:
    def test_public_codes_round_trip_without_collisions(self):
        assert len(INTERNAL_CODES) == len(PUBLIC_CODES)
        assert all(INTERNAL_CODES[public] == internal for internal, public in PUBLIC_CODES.items())

    def test_the_vocabulary_is_the_size_it_is_documented_to_be(self):
        """The counts are load-bearing prose: the spec, the role editor's checklist and every
        review of "what can a role carry" quote them. A permission added or moved between scopes
        without this line moving is a vocabulary change nobody agreed to."""
        assert len(GLOBAL_SCOPE_PERMISSIONS) == 38
        assert len(DATASET_SCOPE_PERMISSIONS) == 13
        assert len(PERMISSION_ENTITIES) == 10

    def test_every_declared_permission_is_grantable(self):
        assert set(PUBLIC_CODES) == set(GLOBAL_SCOPE_PERMISSIONS)

    def test_dataset_scope_is_a_subset_of_global_scope(self):
        assert set(DATASET_SCOPE_PERMISSIONS) < set(GLOBAL_SCOPE_PERMISSIONS)

    def test_entity_labels_are_title_cased_for_the_entity_permission_form(self):
        assert entity_label("AGENTIC_EXECUTION") == "Agentic Execution"
        assert entity_label("SERVICE_ACCOUNT") == "Service Account"
        assert entity_label("DATASET") == "Dataset"


@pytest.mark.django_db
class TestDeclaredPermissionsExistInTheDatabase:
    def test_every_declared_code_has_a_permission_row(self):
        missing = [
            code
            for code, codename in INTERNAL_CODES.items()
            if not Permission.objects.filter(
                content_type__app_label=codename.split(".")[0], codename=codename.split(".")[1]
            ).exists()
        ]

        assert missing == []


class TestPermissionDependencies:
    def test_every_code_in_the_dependency_map_is_declared(self):
        referenced = set(PERMISSION_DEPENDENCIES) | {
            dependent for dependents in PERMISSION_DEPENDENCIES.values() for dependent in dependents
        }

        assert referenced <= set(PUBLIC_CODES)

    def test_dependencies_within_keeps_every_requirement_in_the_global_scope(self):
        assert set(dependencies_within(GLOBAL_SCOPE_PERMISSIONS)) == set(PERMISSION_DEPENDENCIES)

    def test_a_requirement_of_a_requirement_is_reported_against_the_permission_itself(self):
        within_global = dependencies_within(GLOBAL_SCOPE_PERMISSIONS)

        assert PERMISSIONS.GROUP.ASSIGN in within_global[PERMISSIONS.DATASET_ROLE.ASSIGN]
        assert PERMISSIONS.GROUP.ASSIGN in within_global[PERMISSIONS.DATASET.VIEW]
        assert PERMISSIONS.GROUP.ASSIGN not in PERMISSION_DEPENDENCIES[PERMISSIONS.DATASET.VIEW]

    def test_the_closure_is_closed(self):
        """The property the walk exists to hold: if A requires B and B requires C, A requires C."""
        within_global = dependencies_within(GLOBAL_SCOPE_PERMISSIONS)
        requirements: dict[str, set[str]] = {}
        for required, dependents in within_global.items():
            for dependent in dependents:
                requirements.setdefault(dependent, set()).add(required)

        unclosed = {
            (dependent, step)
            for dependent, required in requirements.items()
            for code in required
            for step in requirements.get(code, set())
            if step not in required
        }

        assert unclosed == set()

    def test_the_closure_adds_no_requirement_that_was_never_authored(self):
        """Derived, not authored: every pair it reports has to be reachable through the map as
        written, so the closure cannot invent a requirement nobody agreed to."""
        assert set(dependencies_within(GLOBAL_SCOPE_PERMISSIONS)) == set(PERMISSION_DEPENDENCIES)
        assert all(
            set(dependents) <= set(GLOBAL_SCOPE_PERMISSIONS)
            for dependents in dependencies_within(GLOBAL_SCOPE_PERMISSIONS).values()
        )

    def test_dependencies_within_drops_what_the_scope_cannot_grant(self):
        within_dataset = dependencies_within(DATASET_SCOPE_PERMISSIONS)
        grantable = set(DATASET_SCOPE_PERMISSIONS)

        assert set(within_dataset) == set(PERMISSION_DEPENDENCIES) & grantable
        assert all(set(dependents) <= grantable for dependents in within_dataset.values())
        assert PERMISSIONS.DATASET.VIEW not in within_dataset


class TestTheClosureRefusesACyclicMap:
    """A cycle has a well-defined closure - everything in it requires everything else, grantable
    only all at once - so nothing would fail at runtime. That is the problem: it would read as a
    permission that mysteriously drags others along. `PERMISSION_DEPENDENCIES` is built at import,
    so this fails the process rather than one request."""

    def test_the_map_the_application_ships_builds(self):
        assert build_transitive_dependencies(PERMISSION_DEPENDENCIES)

    def test_a_permission_that_requires_itself_is_refused(self):
        with pytest.raises(ImproperlyConfigured, match="a.b transitively require themselves"):
            build_transitive_dependencies({"a.b": ["a.b"]})

    def test_two_permissions_that_require_each_other_are_refused(self):
        with pytest.raises(ImproperlyConfigured, match="a.b, c.d"):
            build_transitive_dependencies({"a.b": ["c.d"], "c.d": ["a.b"]})

    def test_a_cycle_reached_through_a_third_permission_is_refused(self):
        with pytest.raises(ImproperlyConfigured, match="a.b, c.d, e.f"):
            build_transitive_dependencies({"a.b": ["e.f"], "c.d": ["a.b"], "e.f": ["c.d"]})

    def test_a_chain_that_rejoins_without_looping_is_fine(self):
        """Two paths to the same requirement is a diamond, not a cycle - `group.assign` reaches
        `user.view` both directly and through `global_role.assign`, and that has to stay legal."""
        assert build_transitive_dependencies({"a.b": ["c.d", "e.f"], "c.d": ["e.f"]}) == {
            "a.b": ["c.d", "e.f"],
            "c.d": ["e.f"],
        }
