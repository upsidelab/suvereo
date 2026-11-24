from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.db.models import Q


class RoleBackend(ModelBackend):
    def _get_user_permissions(self, user_obj):
        return Permission.objects.none()

    def _get_group_permissions(self, user_obj):
        return Permission.objects.filter(Q(globalrole__members=user_obj) | Q(globalrole__holders__members=user_obj))
