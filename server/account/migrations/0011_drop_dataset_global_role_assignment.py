from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0010_user_groups"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.DeleteModel(name="DatasetGlobalRoleAssignment"),
    ]
