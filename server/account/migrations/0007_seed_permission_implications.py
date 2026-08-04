from django.db import migrations

# (manage app_label, manage model, manage codename) -> (view app_label, view model, view
# codename). Checking the manage permission in the composer should also check the view
# permission -- was previously hardcoded on the frontend (permission-checklist.tsx's
# MANAGE_IMPLIES_VIEW), now the single source of truth lives here instead.
IMPLICATIONS = [
    (("account", "user", "manage_users"), ("account", "user", "view_users")),
    (("account", "user", "manage_service_accounts"), ("account", "user", "view_service_accounts")),
    (("catalog", "dataset", "manage_datasets"), ("catalog", "dataset", "view_all_datasets")),
    (("catalog", "dataset", "manage_agents"), ("catalog", "dataset", "view_dataset")),
    (("catalog", "dataset", "manage_integrations"), ("catalog", "dataset", "view_integrations")),
    (("catalog", "dataset", "manage_all_agents"), ("catalog", "dataset", "view_all_datasets")),
    (("catalog", "dataset", "manage_all_integrations"), ("catalog", "dataset", "view_all_integrations")),
]

# manage_users/view_users' original descriptions claimed the holder can "change roles" --
# overstated, since assigning an Admin-equivalent group is blocked for anyone but an actual
# Admin (assert_group_ids_assignable). Corrected here rather than in 0004, which is the seed
# migration other permissions' dependencies key off of.
DESCRIPTION_FIXES = [
    ("account", "manage_users", "Can create, edit, and delete user accounts."),
    ("account", "view_users", "Can see the list of users, without editing."),
]


def seed_implications_and_fix_descriptions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    PermissionDescription = apps.get_model("account", "PermissionDescription")

    for (manage_app, manage_model, manage_codename), (view_app, view_model, view_codename) in IMPLICATIONS:
        manage_permission = Permission.objects.get(
            content_type=ContentType.objects.get(app_label=manage_app, model=manage_model),
            codename=manage_codename,
        )
        view_permission = Permission.objects.get(
            content_type=ContentType.objects.get(app_label=view_app, model=view_model),
            codename=view_codename,
        )
        description = PermissionDescription.objects.get(permission=manage_permission)
        description.implied_view_permission = view_permission
        description.save(update_fields=["implied_view_permission"])

    for app_label, codename, new_description in DESCRIPTION_FIXES:
        content_type = ContentType.objects.get(app_label=app_label, model="user")
        permission = Permission.objects.get(content_type=content_type, codename=codename)
        description = PermissionDescription.objects.get(permission=permission)
        description.description = new_description
        description.save(update_fields=["description"])


def reverse_seed_implications_and_fix_descriptions(apps, schema_editor):
    PermissionDescription = apps.get_model("account", "PermissionDescription")
    PermissionDescription.objects.update(implied_view_permission=None)
    # Reversing the description text isn't meaningful (0004's originals were the inaccurate
    # ones this migration corrects) -- leaving the corrected text in place on rollback.


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0006_permissiondescription_implied_view_permission"),
    ]

    operations = [
        migrations.RunPython(seed_implications_and_fix_descriptions, reverse_seed_implications_and_fix_descriptions),
    ]
