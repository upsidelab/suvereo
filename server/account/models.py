from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models

from account.authorization import (
    PERM_CONVERSE,
    PERM_VIEW_ALL_DATASETS,
    PERM_VIEW_DATASET,
    has_dataset_perm,
    is_application_admin,
)


class UserManager(BaseUserManager):
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
    is_service_account = models.BooleanField(default=False)

    objects = UserManager()

    class Meta:
        permissions = [
            ("manage_users", "Can manage human users"),
            ("view_users", "Can view human users"),
            ("manage_service_accounts", "Can manage service accounts"),
            ("view_service_accounts", "Can view service accounts"),
        ]

    @property
    def is_admin(self) -> bool:
        """Application admin flag derived from Admin group membership."""
        return is_application_admin(self)

    def __str__(self):
        return self.email

    def has_dataset_access(self, dataset):
        """True when the user holds catalog.view_all_datasets or a role on this dataset."""
        return self.has_perm(PERM_VIEW_ALL_DATASETS) or has_dataset_perm(self, PERM_VIEW_DATASET, dataset)

    def can_converse(self, dataset):
        """True when the user holds catalog.converse on this dataset (globally or per-object).

        Distinct from has_dataset_access: view_dataset lets you see a dataset exists/browse
        its catalog content, converse is specifically the ability to chat with its agents.
        """
        return has_dataset_perm(self, PERM_CONVERSE, dataset)


class DatasetRole(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(
        Permission,
        limit_choices_to={"content_type__app_label": "catalog", "content_type__model": "dataset"},
    )

    def __str__(self):
        return self.name


class PermissionDescription(models.Model):
    permission = models.OneToOneField(Permission, on_delete=models.CASCADE, related_name="description_entry")
    description = models.TextField()

    def __str__(self):
        return f"{self.permission.codename}: {self.description}"
