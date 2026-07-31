from django.db import migrations


def rename_dataset_access_permissions(apps, schema_editor):
    """Rename access_dataset -> view_dataset and access_all_datasets -> view_all_datasets
    in place, on the existing Permission rows, so every Group.permissions row and every
    guardian UserObjectPermission/GroupObjectPermission row (both reference the Permission
    by primary key, not codename) keeps working unchanged.

    Both source rows are guaranteed to already exist at this point: access_dataset was
    explicitly created in catalog.0015's migrate_users_to_editor_grants, and
    access_all_datasets was explicitly created in account.0003's create_admin_group.

    Django also auto-generated its own builtin "view_dataset" permission for this model
    ages ago (default_permissions used to include "view" before this migration's
    AlterModelOptions removes it) -- that pre-existing row must be deleted first, or the
    rename below collides with it on the unique (content_type, codename) constraint.
    Nothing in this app's authorization code ever referenced that Django-generated
    builtin (only the explicit custom permissions declared in Meta.permissions were used),
    so deleting it is safe.
    """
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get(app_label="catalog", model="dataset")

    Permission.objects.filter(content_type=content_type, codename="view_dataset").delete()

    Permission.objects.filter(content_type=content_type, codename="access_dataset").update(
        codename="view_dataset", name="Can view this data set"
    )
    Permission.objects.filter(content_type=content_type, codename="access_all_datasets").update(
        codename="view_all_datasets", name="Can view all data sets"
    )


def reverse_rename_dataset_access_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type = ContentType.objects.get(app_label="catalog", model="dataset")
    Permission.objects.filter(content_type=content_type, codename="view_dataset").update(
        codename="access_dataset", name="Can access this data set"
    )
    Permission.objects.filter(content_type=content_type, codename="view_all_datasets").update(
        codename="access_all_datasets", name="Can access all data sets"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0015_dataset_permissions_and_access_grants"),
        # access_all_datasets is created in account's migration, not catalog's -- this
        # migration must run after it, or the rename below finds nothing to rename.
        ("account", "0003_admin_group_and_dataset_role"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dataset",
            options={
                "default_permissions": ("add", "change", "delete"),
                "permissions": [
                    ("manage_datasets", "Can manage data sets"),
                    ("view_all_datasets", "Can view all data sets"),
                    ("configure_models", "Can read model provider configuration"),
                    ("view_dataset", "Can view this data set"),
                    ("manage_agents", "Can manage agents in this data set"),
                ],
            },
        ),
        migrations.RunPython(rename_dataset_access_permissions, reverse_rename_dataset_access_permissions),
    ]
