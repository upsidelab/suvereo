from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """Hides internal users, such as the evaluation runner's; use User.all_objects to include them."""

    def get_queryset(self):
        return super().get_queryset().filter(is_internal=False)

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if extra_fields.get("is_service_account", False):
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)

    def create_service_account(self, email, **extra_fields):
        extra_fields.setdefault("is_service_account", True)
        return self._create_user(email, password=None, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    email = models.EmailField(max_length=255, unique=True)
    username = None
    # `PermissionsMixin`'s M2M onto `auth.Group`, which `GlobalRole` replaces. Removed rather than
    # left empty, so it cannot silently answer a question it no longer knows anything about.
    groups = None
    is_service_account = models.BooleanField(default=False)
    is_internal = models.BooleanField(
        default=False, db_comment="Used by Agent Core itself, e.g. evaluation runs; hidden and cannot sign in."
    )

    objects = UserManager()
    all_objects = models.Manager()

    class Meta(AbstractUser.Meta):
        permissions = [
            ("add_serviceaccount", "Can add service account"),
            ("change_serviceaccount", "Can change service account"),
            ("view_serviceaccount", "Can view service account"),
        ]

    def __str__(self):
        return self.email
