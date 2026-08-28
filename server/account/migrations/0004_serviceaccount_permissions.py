from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0003_dataset_role_and_assignments"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": [
                    ("add_serviceaccount", "Can add service account"),
                    ("change_serviceaccount", "Can change service account"),
                    ("view_serviceaccount", "Can view service account"),
                ],
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
    ]
