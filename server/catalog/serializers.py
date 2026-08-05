from rest_framework import serializers

from account.authorization import DATASET_PERMISSION_CODENAMES, has_dataset_perm
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
    "permissions",
]


class DataSetSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = DataSet
        fields = DATASET_FIELDS
        read_only_fields = ["id", "permissions"]

    def get_permissions(self, obj):
        """The subset of DATASET_PERMISSION_CODENAMES the requesting user holds on this
        specific dataset. Lets the frontend show/hide dataset-scoped manage controls
        (Agents, Integrations) per-permission instead of relying solely on a backend 403."""
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return []
        return [codename for codename in DATASET_PERMISSION_CODENAMES if has_dataset_perm(request.user, codename, obj)]


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
    name = serializers.SerializerMethodField()
    integration_type_name = serializers.SerializerMethodField()
    syncable = serializers.SerializerMethodField()
    configurable = serializers.SerializerMethodField()

    class Meta:
        model = Integration
        fields = [
            "id",
            "dataset",
            "type",
            "name",
            "integration_type_name",
            "syncable",
            "configurable",
            "config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "dataset", "created_at", "updated_at"]

    def _get_plugin_class(self, integration):
        from catalog.integrations.registry import IntegrationPluginRegistry

        try:
            return IntegrationPluginRegistry().get_plugin_class_by_type(integration.type)
        except KeyError:
            return None

    def get_name(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class.NAME if plugin_class else integration.type

    def get_integration_type_name(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class.INTEGRATION_TYPE_NAME if plugin_class else None

    def get_syncable(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class.is_syncable() if plugin_class else False

    def get_configurable(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class is not None and plugin_class.CONFIGURATION_ARGS is not None


class IntegrationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ["id", "dataset", "type", "config", "created_at", "updated_at"]
        read_only_fields = ["id", "dataset", "type", "created_at", "updated_at"]


class IntegrationTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    integration_type_name = serializers.CharField()
    syncable = serializers.BooleanField()
    config_schema = serializers.JSONField()


class DataSetAccessGrantSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=["user", "group"])
    target_id = serializers.IntegerField()
    role = serializers.CharField()

    def validate_role(self, value):
        from account.models import DatasetRole

        if not DatasetRole.objects.filter(name=value).exists():
            raise serializers.ValidationError("Unknown dataset role.")
        return value


class DataSetAccessSerializer(serializers.Serializer):
    target_type = serializers.CharField()
    target_id = serializers.IntegerField()
    target_label = serializers.CharField()
    role = serializers.CharField(allow_null=True)
