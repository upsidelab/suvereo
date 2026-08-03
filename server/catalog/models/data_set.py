from django.db import models


class DataSet(models.Model):
    name = models.CharField(max_length=30)
    language_model_provider = models.CharField(default="OpenAI")
    language_model = models.CharField(default="gpt-4o")
    embedding_provider = models.CharField(max_length=255, default="OpenAI")
    embedding_model = models.CharField(max_length=255, default="text-embedding-3-large")
    embedding_vector_dimensions = models.IntegerField(default=512)
    embedding_chunk_size = models.IntegerField(default=3000)
    embedding_chunk_overlap = models.IntegerField(default=150)

    class Meta:
        db_table_comment = (
            "List of various data sets. One data set may be the whole company's content such as blog "
            "posts, or some part of it: a data set may be represent a brand or department."
        )
        default_permissions = ("add", "change", "delete")
        permissions = [
            ("manage_datasets", "Can manage data sets"),
            ("view_all_datasets", "Can view all data sets"),
            ("configure_models", "Can read model provider configuration"),
            ("view_dataset", "Can view this data set"),
            ("manage_agents", "Can manage agents in this data set"),
            ("converse", "Can converse with this data set's agents"),
            ("view_integrations", "Can view this data set's integrations"),
            ("manage_integrations", "Can manage this data set's integrations"),
            ("converse_all_datasets", "Can converse with agents in every data set"),
            ("manage_all_agents", "Can manage agents in every data set"),
            ("view_all_integrations", "Can view every data set's integrations"),
            ("manage_all_integrations", "Can manage every data set's integrations"),
        ]
