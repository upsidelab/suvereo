from django.db import IntegrityError, transaction

from account.models import User

EMAIL = "evaluation@enthusiast.internal"


class EvalUser:
    """The internal service account evaluation conversations belong to; it is inactive and hidden, so it cannot sign in
    or be seen."""

    @staticmethod
    def get() -> User:
        if user := User.all_objects.filter(email=EMAIL).first():
            return user
        try:
            with transaction.atomic():
                return User.objects.create_service_account(EMAIL, is_active=False, is_internal=True)
        except IntegrityError:
            return User.all_objects.get(email=EMAIL)
