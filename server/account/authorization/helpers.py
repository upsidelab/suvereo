from django.db.models import Q, QuerySet
from django.http import Http404

from account.models import DatasetGroupRoleAssignment, DatasetUserRoleAssignment, User
from catalog.models import DataSet

from .permission_codenames import PERMISSIONS


def is_dataset_member(user: User, dataset: DataSet) -> bool:
    if user.has_perm(PERMISSIONS.DATASET.VIEW):
        return True
    if DatasetUserRoleAssignment.objects.filter(user=user, dataset=dataset).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(group__in=user.groups.all(), dataset=dataset).exists()


def datasets_visible_to(user: User) -> QuerySet[DataSet]:
    if user.has_perm(PERMISSIONS.DATASET.VIEW):
        return DataSet.objects.all()
    return DataSet.objects.filter(
        Q(datasetuserroleassignment__user=user) | Q(datasetgrouproleassignment__group__in=user.groups.all())
    ).distinct()


def has_dataset_perm(user: User, codename: str, dataset: DataSet) -> bool:
    if user.has_perm(codename):
        return True
    bare = codename.split(".")[-1]
    if DatasetUserRoleAssignment.objects.filter(user=user, dataset=dataset, role__permissions__codename=bare).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(
        group__in=user.groups.all(), dataset=dataset, role__permissions__codename=bare
    ).exists()


def has_any_dataset_access(user: User) -> bool:
    if user.has_perm(PERMISSIONS.DATASET.VIEW):
        return True
    if DatasetUserRoleAssignment.objects.filter(user=user).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(group__in=user.groups.all()).exists()


def has_any_permission_on_any_dataset(user: User, *codenames: str) -> bool:
    if any(user.has_perm(codename) for codename in codenames):
        return True
    bare_codenames = [codename.split(".")[-1] for codename in codenames]
    if DatasetUserRoleAssignment.objects.filter(user=user, role__permissions__codename__in=bare_codenames).exists():
        return True
    return DatasetGroupRoleAssignment.objects.filter(
        group__in=user.groups.all(), role__permissions__codename__in=bare_codenames
    ).exists()


def enforce_dataset_scoped_permission(view, codename: str, dataset: DataSet, *, obscured_model: type = DataSet) -> None:
    """Holding `codename` (globally, or via a per-dataset role) lets the request through.
    Lacking it while still being a member of `dataset` denies with 403 - the dataset is
    visible to this user, this specific capability on it isn't. Having no relationship to
    `dataset` at all denies with 404, so its existence is never confirmed to someone outside
    it.

    The 404 message mimics Django's own `get_object_or_404` message for `obscured_model` -
    whichever model the caller actually ran its existence check against before reaching here
    (`DataSet` itself in most call sites; e.g. `Agent` when the caller resolved `dataset` from
    an already-fetched agent). Matching that message, rather than leaving this 404 bare, keeps
    "denied access" indistinguishable from "doesn't exist" for the same model - otherwise a
    non-member could tell the two apart by comparing response bodies.
    """
    if has_dataset_perm(view.request.user, codename, dataset):
        return
    if is_dataset_member(view.request.user, dataset):
        view.permission_denied(view.request)
    raise Http404(f"No {obscured_model._meta.object_name} matches the given query.")
