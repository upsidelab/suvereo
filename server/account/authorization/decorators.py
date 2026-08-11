from functools import wraps

from .helpers import has_any_permission_on_any_dataset


def global_permission_required(codename: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not self.request.user.has_perm(codename):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator


def any_global_permission_required(*codenames: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not any(self.request.user.has_perm(codename) for codename in codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator


def any_permission_on_any_dataset_required(*codenames: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not has_any_permission_on_any_dataset(self.request.user, *codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator
