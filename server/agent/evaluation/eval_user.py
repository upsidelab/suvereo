from django.db import IntegrityError, transaction

from account.models import User

EMAIL = "evaluation@enthusiast.internal"


class EvalUser:
    """The service account evaluation conversations belong to; it is inactive, so it cannot sign in."""

    @staticmethod
    def get() -> User:
        if user := User.objects.filter(email=EMAIL).first():
            return user
        try:
            with transaction.atomic():
                return User.objects.create_service_account(EMAIL, is_active=False)
        except IntegrityError:
            return User.objects.get(email=EMAIL)
