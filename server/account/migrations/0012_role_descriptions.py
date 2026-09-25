from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("account", "0011_drop_dataset_global_role_assignment")]

    operations = [
        migrations.AddField(
            model_name="globalrole",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="datasetrole",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="usergroup",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
