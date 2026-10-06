from typing import Any

from enthusiast_common.integrations import BaseOAuthIntegration
from pydantic import ValidationError as PydanticValidationError
from rest_framework import serializers

from account.authorization import dataset_permission_codes
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
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = DataSet
        fields = DATASET_FIELDS + ["permissions"]
        read_only_fields = ["id", "permissions"]

    def get_permissions(self, data_set) -> list[str]:
        """The requesting user's dataset-scoped permissions on this data set"""
        request = self.context.get("request")
        if request is None:
            return []
        return dataset_permission_codes(request.user, data_set)


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


class IntegrationConfigValidationMixin:
    """Checks a stored ``config`` against the plugin's ``CONFIGURATION_ARGS`` before it is saved.

    Without this the API accepts any JSON, and the mistake only surfaces much later: the plugin
    cannot be instantiated, the resolver logs and skips it, and the agent quietly runs without the
    integration's tools. Validating on write turns that silent failure into a 400 the admin can act on.
    """

    def _validate_config(self, integration_type: str | None, config: Any) -> None:
        from catalog.integrations.registry import IntegrationPluginRegistry

        if integration_type is None:
            return
        try:
            plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration_type)
        except KeyError:
            # An unregistered type is reported by the view, which words it better than we can here.
            return
        config_class = plugin_class.CONFIGURATION_ARGS
        if config_class is None:
            return
        try:
            config_class(**config)
        except PydanticValidationError as e:
            raise serializers.ValidationError({"config": self._field_errors(e)}) from e
        except TypeError as e:
            raise serializers.ValidationError({"config": "Configuration must be an object."}) from e

    @staticmethod
    def _field_errors(error: PydanticValidationError) -> dict[str, str]:
        """Flatten pydantic's errors into ``{field: message}``, which the frontend renders per field."""
        return {str(item["loc"][0]) if item["loc"] else "config": item["msg"] for item in error.errors()}


class IntegrationSerializer(IntegrationConfigValidationMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    integration_type_name = serializers.SerializerMethodField()
    syncable = serializers.SerializerMethodField()
    needs_reconnect = serializers.SerializerMethodField()
    configurable = serializers.SerializerMethodField()
    config_schema = serializers.SerializerMethodField()

    class Meta:
        model = Integration
        fields = [
            "id",
            "dataset",
            "type",
            "name",
            "integration_type_name",
            "syncable",
            "needs_reconnect",
            "configurable",
            "config",
            "config_schema",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "dataset", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        self._validate_config(attrs.get("type"), attrs.get("config", {}))
        return attrs

    def _get_plugin_class(self, integration):
        from catalog.integrations.registry import IntegrationPluginRegistry

        try:
            return IntegrationPluginRegistry().get_plugin_class_by_type(integration.type)
        except KeyError:
            return None

    def _build_plugin(self, integration):
        """The configured plugin for this record, built once however many fields ask for it."""
        from catalog.integrations.registry import IntegrationPluginRegistry

        if not hasattr(self, "_plugins"):
            self._plugins = {}
        if integration.pk not in self._plugins:
            try:
                self._plugins[integration.pk] = IntegrationPluginRegistry().build_instance(integration)
            except Exception:
                self._plugins[integration.pk] = None
        return self._plugins[integration.pk]

    def get_name(self, integration):
        """The instance's own label, so several integrations of one type are distinguishable.

        Falls back to the type's name if the plugin cannot be built from the stored config, since a
        listing that breaks on one bad record is worse than one that labels it generically.
        """
        plugin_class = self._get_plugin_class(integration)
        if plugin_class is None:
            return integration.type
        plugin = self._build_plugin(integration)
        try:
            return plugin.instance_name() if plugin else plugin_class.NAME
        except Exception:
            return plugin_class.NAME

    def get_needs_reconnect(self, integration) -> bool:
        """Whether this instance has stopped working in a way only a person can put right."""
        plugin = self._build_plugin(integration)
        if not isinstance(plugin, BaseOAuthIntegration):
            return False
        try:
            return bool(plugin.needs_reconnect())
        except Exception:
            return False

    def get_integration_type_name(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class.INTEGRATION_TYPE_NAME if plugin_class else None

    def get_syncable(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class.is_syncable() if plugin_class else False

    def get_config_schema(self, integration) -> dict:
        plugin_class = self._get_plugin_class(integration)
        return plugin_class().get_config_schema() if plugin_class else {}

    def get_configurable(self, integration):
        plugin_class = self._get_plugin_class(integration)
        return plugin_class is not None and plugin_class.CONFIGURATION_ARGS is not None


class IntegrationUpdateSerializer(IntegrationConfigValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ["id", "dataset", "type", "config", "created_at", "updated_at"]
        read_only_fields = ["id", "dataset", "type", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "config" in attrs:
            # type is read-only on update, so the instance is the only source for it.
            self._validate_config(self.instance.type, attrs["config"])
        return attrs


class IntegrationTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    integration_type_name = serializers.CharField()
    syncable = serializers.BooleanField()
    supports_oauth = serializers.BooleanField()
    oauth_field = serializers.CharField(allow_blank=True)
    oauth_refresh_field = serializers.CharField(allow_blank=True)
    config_schema = serializers.JSONField()
