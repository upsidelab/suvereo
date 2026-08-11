from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission

from .models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment, User


@admin.register(User)
class UserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("password",)}),
        (("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            ("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "usable_password", "password1", "password2"),
            },
        ),
    )

    list_display = ("email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("first_name", "last_name", "email")
    ordering = ("email",)


# NOTE: temporary manual-testing scaffolding — registers the models that back the permissions
# refactor (specs/permissions-implementation-plan.md) so role/grant setup for each phase can be
# done by hand here instead of via seed scripts or front-running Phase 8's real endpoints. Deleted
# as part of Phase 8's admin cleanup, alongside deregistering User/DataSet/Integration and dropping
# the /admin URL include.


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "name", "content_type")
    list_filter = ("content_type",)
    search_fields = ("codename", "name")


@admin.register(DatasetRole)
class DatasetRoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    filter_horizontal = ("permissions",)


@admin.register(DatasetUserRoleAssignment)
class DatasetUserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "dataset", "role")
    list_filter = ("dataset", "role")
    search_fields = ("user__email", "dataset__name")


@admin.register(DatasetGroupRoleAssignment)
class DatasetGroupRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("group", "dataset", "role")
    list_filter = ("dataset", "role")
    search_fields = ("group__name", "dataset__name")
