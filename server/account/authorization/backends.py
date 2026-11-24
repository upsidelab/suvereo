from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet

from account.models import User


class RoleBackend(ModelBackend):
    def _get_user_permissions(self, user_obj: User) -> QuerySet[Permission]:
        return Permission.objects.none()

    def _get_group_permissions(self, user_obj: User) -> QuerySet[Permission]:
        return Permission.objects.filter(Q(globalrole__members=user_obj) | Q(globalrole__holders__members=user_obj))
