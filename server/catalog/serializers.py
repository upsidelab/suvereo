from rest_framework import serializers

from agent.core.registries.embeddings.embedding_provider_registry import EmbeddingProviderRegistry

from .models import DataSet, Integration

DATASET_FIELDS = [
    "id",
    "name",
    "language_model_provider",
    "language_model",
    "embedding_provider",
    "embedding_model",
    "embedding_vector_dimensions",
    "embedding_chunk_size",
    "embedding_chunk_overlap",
]


class DataSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSet
        fields = DATASET_FIELDS
        read_only_fields = ["id"]


class DataSetCreateSerializer(DataSetSerializer):
    preconfigure_agents = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta(DataSetSerializer.Meta):
        fields = DataSetSerializer.Meta.fields + ["preconfigure_agents"]

    def validate(self, data):
        """Validate that embedding_vector_dimensions satisfies provider constraints."""
        embedding_provider = data.get("embedding_provider")
        embedding_model = data.get("embedding_model")
        embedding_vector_dimensions = data.get("embedding_vector_dimensions")

        if embedding_provider and embedding_model and embedding_vector_dimensions is not None:
            try:
                provider_class = EmbeddingProviderRegistry().provider_class_by_name(embedding_provider)
            except Exception:
                provider_class = None

            if provider_class is not None:
                constraints = provider_class.vector_size_constraints()
                allowed_sizes = constraints.get(embedding_model)
                if allowed_sizes and embedding_vector_dimensions not in allowed_sizes:
                    raise serializers.ValidationError(
                        {
                            "embedding_vector_dimensions": (
                                f"Model '{embedding_model}' only supports vector sizes: "
                                f"{allowed_sizes}. Got {embedding_vector_dimensions}."
                            )
                        }
                    )

        return data


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ["id", "dataset", "type", "config", "created_at", "updated_at"]
        read_only_fields = ["id", "dataset", "created_at", "updated_at"]


class IntegrationTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    config_schema = serializers.JSONField()
