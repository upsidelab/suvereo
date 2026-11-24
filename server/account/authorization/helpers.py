from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet
from django.http import Http404

from account.authorization.permission_codenames import PERMISSIONS
from account.authorization.permission_codes import PUBLIC_CODES
from account.authorization.permission_rules import DATASET_SCOPE_PERMISSIONS
from account.models import DatasetGroupRoleAssignment, DatasetUserRoleAssignment, User
from catalog.models import DataSet


def _permissions(*labels: str) -> QuerySet[Permission]:
    if not labels:
        return Permission.objects.none()
    query = Q()
    for label in labels:
        app_label, codename = label.split(".", 1)
        query |= Q(content_type__app_label=app_label, codename=codename)
    return Permission.objects.filter(query)


def is_dataset_member(user: User, dataset: DataSet) -> bool:
    if user.has_perm(PERMISSIONS.DATA_SET.VIEW):
        return True
    if DatasetUserRoleAssignment.objects.filter(user=user, dataset=dataset).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(group__members=user, dataset=dataset).exists()


def datasets_visible_to(user: User) -> QuerySet[DataSet]:
    data_sets = DataSet.objects.all()
    if user.has_perm(PERMISSIONS.DATA_SET.VIEW):
        return data_sets
    return data_sets.filter(
        Q(datasetuserroleassignment__user=user) | Q(datasetgrouproleassignment__group__members=user)
    ).distinct()


def has_dataset_perm(user: User, codename: str, dataset: DataSet) -> bool:
    if user.has_perm(codename):
        return True
    permissions = _permissions(codename)
    if DatasetUserRoleAssignment.objects.filter(
        user=user, dataset=dataset, role__permissions__in=permissions
    ).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(
        group__members=user, dataset=dataset, role__permissions__in=permissions
    ).exists()


def dataset_permission_codes(user: User, dataset: DataSet) -> list[str]:
    held = {codename for codename in DATASET_SCOPE_PERMISSIONS if user.has_perm(codename)}

    assignment_rows = [
        *DatasetUserRoleAssignment.objects.filter(user=user, dataset=dataset).values_list(
            "role__permissions__content_type__app_label", "role__permissions__codename"
        ),
        *DatasetGroupRoleAssignment.objects.filter(group__members=user, dataset=dataset).values_list(
            "role__permissions__content_type__app_label", "role__permissions__codename"
        ),
    ]
    held |= {f"{app_label}.{codename}" for app_label, codename in assignment_rows if codename}

    return sorted(PUBLIC_CODES[codename] for codename in held & set(DATASET_SCOPE_PERMISSIONS))


def datasets_with_permission(user: User, codename: str) -> QuerySet[DataSet]:
    if user.has_perm(codename):
        return DataSet.objects.all()
    permissions = _permissions(codename)
    return DataSet.objects.filter(
        Q(datasetuserroleassignment__user=user, datasetuserroleassignment__role__permissions__in=permissions)
        | Q(
            datasetgrouproleassignment__group__members=user,
            datasetgrouproleassignment__role__permissions__in=permissions,
        )
    ).distinct()


def has_any_dataset_access(user: User) -> bool:
    if user.has_perm(PERMISSIONS.DATA_SET.VIEW):
        return True
    if DatasetUserRoleAssignment.objects.filter(user=user).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(group__members=user).exists()


def has_any_permission_on_any_dataset(user: User, *codenames: str) -> bool:
    if any(user.has_perm(codename) for codename in codenames):
        return True
    permissions = _permissions(*codenames)
    if DatasetUserRoleAssignment.objects.filter(user=user, role__permissions__in=permissions).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(
        group__members=user, role__permissions__in=permissions
    ).exists()


def enforce_any_dataset_scoped_permission(
    view, dataset: DataSet, *codenames: str, obscured_model: type = DataSet
) -> None:
    if any(has_dataset_perm(view.request.user, codename, dataset) for codename in codenames):
        return
    if is_dataset_member(view.request.user, dataset):
        view.permission_denied(view.request)
    raise Http404(f"No {obscured_model._meta.object_name} matches the given query.")


def enforce_dataset_scoped_permission(view, codename: str, dataset: DataSet, *, obscured_model: type = DataSet) -> None:
    enforce_any_dataset_scoped_permission(view, dataset, codename, obscured_model=obscured_model)
