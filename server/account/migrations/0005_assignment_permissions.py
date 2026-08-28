from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_serviceaccount_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="datasetrole",
            options={
                "permissions": [
                    ("assign_datasetrole", "Can assign dataset roles to users and groups"),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": [
                    ("add_serviceaccount", "Can add service account"),
                    ("change_serviceaccount", "Can change service account"),
                    ("view_serviceaccount", "Can view service account"),
                    ("assign_group", "Can add users to and remove them from groups"),
                ],
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
    ]
