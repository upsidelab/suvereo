from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0032_remove_prompt_extension_from_agent_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="is_temporary",
            field=models.BooleanField(
                default=False,
                db_comment="Created for a short-lived purpose, e.g. an evaluation run; hidden and deleted after.",
            ),
        ),
    ]
