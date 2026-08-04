from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

from account.authorization import PERM_CONVERSE, PERM_VIEW_DATASET, has_dataset_perm, is_application_admin


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
        return has_dataset_perm(self, PERM_VIEW_DATASET, dataset)

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


class DatasetUserRoleAssignment(models.Model):
    """Records which DatasetRole a user's dataset grant was made through.

    guardian's UserObjectPermission stores only the resulting permission grants, not which
    named role produced them -- reconstructing "what role does this user have on this dataset"
    from the permission set alone is ambiguous whenever one role's permissions are a subset of
    another's, or two roles happen to grant the same set. This table is the source of truth
    instead; the actual access enforcement still goes entirely through guardian's grants.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dataset_role_assignments")
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE, related_name="user_role_assignments")
    role = models.ForeignKey(DatasetRole, on_delete=models.CASCADE, related_name="user_assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "dataset"], name="unique_dataset_user_role_assignment"),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.role.name} on dataset {self.dataset_id}"


class DatasetGroupRoleAssignment(models.Model):
    """Records which DatasetRole a group's dataset grant was made through -- see
    DatasetUserRoleAssignment for why this is tracked separately from the guardian grants
    themselves."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="dataset_role_assignments")
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE, related_name="group_role_assignments")
    role = models.ForeignKey(DatasetRole, on_delete=models.CASCADE, related_name="group_assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "dataset"], name="unique_dataset_group_role_assignment"),
        ]

    def __str__(self):
        return f"{self.group.name} -> {self.role.name} on dataset {self.dataset_id}"


class PermissionDescription(models.Model):
    """Attaches a human-readable description to a `Permission`.

    Every migration that creates a new permission must also seed a `PermissionDescription` row for it, in that
    same migration, following the pattern in `0004_add_permission_descriptions.py`.
    """

    permission = models.OneToOneField(Permission, on_delete=models.CASCADE, related_name="description_entry")
    description = models.TextField()
    implied_view_permission = models.ForeignKey(
        Permission,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Set on a manage_X permission's own row when checking it should also check a view_X "
        "permission in the composer, the single source of truth the frontend checklist reads"
    )

    def __str__(self):
        return f"{self.permission.codename}: {self.description}"
