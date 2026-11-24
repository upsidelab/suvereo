from collections.abc import Callable
from functools import wraps
from typing import Any

from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization.helpers import has_any_permission_on_any_dataset


def global_permission_required(codename: str) -> Callable[[Callable], Callable]:
    def decorator(view_method: Callable) -> Callable:
        @wraps(view_method)
        def wrapper(self: APIView, *args: Any, **kwargs: Any) -> Response:
            if not self.request.user.has_perm(codename):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator


def any_global_permission_required(*codenames: str) -> Callable[[Callable], Callable]:
    def decorator(view_method: Callable) -> Callable:
        @wraps(view_method)
        def wrapper(self: APIView, *args: Any, **kwargs: Any) -> Response:
            if not any(self.request.user.has_perm(codename) for codename in codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_method: Callable) -> Callable:
    @wraps(view_method)
    def wrapper(self: APIView, *args: Any, **kwargs: Any) -> Response:
        if not self.request.user.is_superuser:
            self.permission_denied(self.request)
        return view_method(self, *args, **kwargs)

    return wrapper


def any_permission_on_any_dataset_required(*codenames: str) -> Callable[[Callable], Callable]:
    def decorator(view_method: Callable) -> Callable:
        @wraps(view_method)
        def wrapper(self: APIView, *args: Any, **kwargs: Any) -> Response:
            if not has_any_permission_on_any_dataset(self.request.user, *codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator
