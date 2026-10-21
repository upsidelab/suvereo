from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0017_allow_multiple_integration_instances_per_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="is_temporary",
            field=models.BooleanField(
                default=False,
                db_comment="Created for a short-lived purpose, e.g. an evaluation run; hidden and deleted after.",
            ),
        ),
    ]
