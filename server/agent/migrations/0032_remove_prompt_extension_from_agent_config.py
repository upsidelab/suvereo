from django.db import migrations


def remove_prompt_extension(apps, schema_editor):
    Agent = apps.get_model("agent", "Agent")
    for agent in Agent.objects.all():
        if "prompt_extension" in agent.config:
            del agent.config["prompt_extension"]
            agent.save(update_fields=["config"])


class Migration(migrations.Migration):

    dependencies = [
        ("agent", "0031_conversation_converse_permission"),
    ]

    operations = [
        migrations.RunPython(remove_prompt_extension, migrations.RunPython.noop),
    ]
