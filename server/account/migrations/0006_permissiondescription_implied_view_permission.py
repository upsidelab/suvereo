import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0005_datasetgrouproleassignment_datasetuserroleassignment"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="permissiondescription",
            name="implied_view_permission",
            field=models.ForeignKey(
                blank=True,
                help_text="Set on a manage_X permission's own row when checking it should also check a "
                "view_X permission in the composer -- the single source of truth the frontend checklist "
                "reads instead of hardcoding the pairing.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="auth.permission",
            ),
        ),
    ]
