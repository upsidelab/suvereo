from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0005_assignment_permissions"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="datasetuserroleassignment",
            unique_together={("user", "dataset", "role")},
        ),
        migrations.AlterUniqueTogether(
            name="datasetglobalroleassignment",
            unique_together={("global_role", "dataset", "role")},
        ),
    ]
