from functools import wraps

from django.db.models import Q, QuerySet
from rest_framework.permissions import BasePermission

from account.models import DatasetGroupRoleAssignment, DatasetUserRoleAssignment, User
from account.permission_codenames import PERMISSIONS
from catalog.models import DataSet


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


def required_permission(codename: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not self.request.user.has_perm(codename):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
