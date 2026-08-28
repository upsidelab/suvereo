import pytest
from django.contrib.auth.models import Permission

from account.authorization import (
    DATASET_SCOPE_PERMISSIONS,
    GLOBAL_SCOPE_PERMISSIONS,
    INTERNAL_CODES,
    PERMISSION_DEPENDENCIES,
    PERMISSIONS,
    PUBLIC_CODES,
    dependencies_within,
    entity_label,
)


class TestPermissionVocabulary:
    def test_public_codes_round_trip_without_collisions(self):
        assert len(INTERNAL_CODES) == len(PUBLIC_CODES)
        assert all(INTERNAL_CODES[public] == internal for internal, public in PUBLIC_CODES.items())

    def test_every_declared_permission_is_grantable(self):
        assert set(PUBLIC_CODES) == set(GLOBAL_SCOPE_PERMISSIONS)

    def test_dataset_scope_is_a_subset_of_global_scope(self):
        assert set(DATASET_SCOPE_PERMISSIONS) < set(GLOBAL_SCOPE_PERMISSIONS)

    def test_entity_labels_read_as_prose(self):
        assert entity_label("AGENTIC_EXECUTION") == "Agentic execution"
        assert entity_label("SERVICE_ACCOUNT") == "Service account"


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

    def test_dependencies_within_drops_what_the_scope_cannot_grant(self):
        within_dataset = dependencies_within(DATASET_SCOPE_PERMISSIONS)
        grantable = set(DATASET_SCOPE_PERMISSIONS)

        assert set(within_dataset) == set(PERMISSION_DEPENDENCIES) & grantable
        assert all(set(dependents) <= grantable for dependents in within_dataset.values())
        assert PERMISSIONS.DATASET.VIEW not in within_dataset