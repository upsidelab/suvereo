from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from account.models import User


class RefreshTokenRevocationService:
    def revoke_all(self, user: User) -> None:
        outstanding_tokens = OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now())
        BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=token) for token in outstanding_tokens], ignore_conflicts=True
        )
