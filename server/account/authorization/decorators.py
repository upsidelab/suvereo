from functools import wraps


def permission_required(codename: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not self.request.user.has_perm(codename):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator


def any_permission_required(*codenames: str):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, *args, **kwargs):
            if not any(self.request.user.has_perm(codename) for codename in codenames):
                self.permission_denied(self.request)
            return view_method(self, *args, **kwargs)

        return wrapper

    return decorator
