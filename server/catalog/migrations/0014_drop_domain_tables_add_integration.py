import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0013_ecommerceintegration"),
    ]

    operations = [
        migrations.DeleteModel(name="ECommerceIntegration"),
        migrations.DeleteModel(name="ProductSource"),
        migrations.DeleteModel(name="DocumentSource"),
        migrations.DeleteModel(name="ProductContentChunk"),
        migrations.DeleteModel(name="DocumentChunk"),
        migrations.DeleteModel(name="Product"),
        migrations.DeleteModel(name="Document"),
        migrations.CreateModel(
            name="Integration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(max_length=128)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="integrations",
                        to="catalog.dataset",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("dataset", "type"), name="unique_integration_type_per_dataset")
                ],
            },
        ),
    ]
