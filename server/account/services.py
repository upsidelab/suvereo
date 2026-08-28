from django.conf import settings

from .models import User


class ServiceAccountNameService:
    def generate_service_account_email(self, name: str) -> str:
        """
        Generate a service account email based on the provided name.
        """
        return f"{name}@{settings.SERVICE_ACCOUNT_DOMAIN}"

    def is_service_account_name_available(self, name: str, exclude_user: User | None = None) -> bool:
        """
        Check if the provided service account name is available.

        Pass `exclude_user` when validating a rename, so an account keeping its own name
        isn't reported as colliding with itself.
        """
        email = self.generate_service_account_email(name)
        candidates = User.objects.filter(email=email)
        if exclude_user is not None:
            candidates = candidates.exclude(pk=exclude_user.pk)
        return not candidates.exists()
