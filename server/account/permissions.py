from rest_framework.permissions import BasePermission

from account.authorization import is_application_admin


class HasRequiredPermission(BasePermission):
    """Authorize the request against the view's ``required_permission`` attribute.

    Views declare e.g. ``required_permission = "account.manage_users"``; the
    request is allowed when ``request.user.has_perm(required_permission)``.
    A view missing the attribute is treated as misconfigured and denied.
    """

    def has_permission(self, request, view):
        required_permission = getattr(view, "required_permission", None)
        if required_permission is None:
            return False
        return bool(request.user and request.user.has_perm(required_permission))


class IsApplicationAdmin(BasePermission):
    """Authorize the request only for Admin-group members (or superusers).

    Used for role/permission management endpoints instead of HasRequiredPermission — a
    delegable "manage_roles" permission would let its holder grant themselves any other
    permission, including effectively promoting themselves to Admin.
    """

    def has_permission(self, request, view):
        return bool(request.user and is_application_admin(request.user))
