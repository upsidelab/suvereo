from django.conf import settings

from account.models import User


class ServiceAccountNameService:
    def generate_service_account_email(self, name: str) -> str:
        return f"{name}@{settings.SERVICE_ACCOUNT_DOMAIN}"

    def is_service_account_name_available(self, name: str, exclude_user: User | None = None) -> bool:
        email = self.generate_service_account_email(name)
        candidates = User.objects.filter(email=email)
        if exclude_user is not None:
            candidates = candidates.exclude(pk=exclude_user.pk)
        return not candidates.exists()
