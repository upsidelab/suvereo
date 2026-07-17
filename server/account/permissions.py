from rest_framework.permissions import BasePermission


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
