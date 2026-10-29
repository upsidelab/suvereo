from django.db import IntegrityError, transaction

from account.models import User
from account.services import ServiceAccountNameService

NAME = "evaluation"


class EvalUser:
    """The internal service account evaluation conversations belong to; it is inactive and hidden, so it cannot sign in
    or be seen."""

    @staticmethod
    def email() -> str:
        return ServiceAccountNameService().generate_service_account_email(NAME)

    @staticmethod
    def get() -> User:
        email = EvalUser.email()
        if user := User.all_objects.filter(email=email).first():
            return user
        try:
            with transaction.atomic():
                return User.objects.create_service_account(email, is_active=False, is_internal=True)
        except IntegrityError:
            return User.all_objects.get(email=email)
