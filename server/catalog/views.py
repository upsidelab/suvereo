from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from guardian.shortcuts import get_groups_with_perms, get_objects_for_user, get_users_with_perms
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.authorization import (
    PERM_ACCESS_ALL_DATASETS,
    PERM_ACCESS_DATASET,
    PERM_CONFIGURE_MODELS,
    PERM_MANAGE_DATASETS,
    assign_dataset_role,
    remove_all_dataset_grants,
)
from account.models import User
from account.permissions import HasRequiredPermission, IsApplicationAdmin
from agent.core.registries.embeddings import EmbeddingProviderRegistry
from agent.core.registries.language_models import LanguageModelRegistry
from agent.models import AgenticExecution, Message
from agent.models.conversation import ConversationFile
from agent.services import AgentPreconfigurationService

from .models import DataSet
from .serializers import (
    DataSetAccessGrantSerializer,
    DataSetAccessSerializer,
    DataSetCreateSerializer,
    DataSetSerializer,
)


class DataSetListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DataSetCreateSerializer
        return DataSetSerializer

    @swagger_auto_schema(operation_description="List data sets")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.user.has_perm(PERM_ACCESS_ALL_DATASETS):
            return DataSet.objects.all()

        return get_objects_for_user(self.request.user, PERM_ACCESS_DATASET)

    @swagger_auto_schema(operation_description="Create a new data set", request_body=DataSetCreateSerializer)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        if not self.request.user.has_perm(PERM_MANAGE_DATASETS):
            self.permission_denied(self.request)

        with transaction.atomic():
            preconfigure_agents = serializer.validated_data.pop("preconfigure_agents")
            data_set = serializer.save()
            assign_dataset_role(self.request.user, data_set, "editor")
            if preconfigure_agents:
                AgentPreconfigurationService.preconfigure_available_agents(data_set)


class DataSetDetailView(RetrieveAPIView):
    serializer_class = DataSetSerializer
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_MANAGE_DATASETS
    lookup_url_kwarg = "data_set_id"
    queryset = DataSet.objects.all()

    @swagger_auto_schema(
        operation_description="Retrieve a data set by ID",
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a data set (embedding fields are ignored)",
        request_body=DataSetSerializer,
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
            )
        ],
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()

        # Filter out embedding fields from the request data
        filtered_data = {
            k: v
            for k, v in request.data.items()
            if k not in ["embedding_provider", "embedding_model", "embedding_vector_dimensions"]
        }

        serializer = self.get_serializer(instance, data=filtered_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Delete a data set",
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
            )
        ],
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            Message.objects.filter(conversation__data_set=instance).delete()
            ConversationFile.objects.filter(conversation__data_set=instance).delete()
            AgenticExecution.objects.filter(conversation__data_set=instance).delete()
            instance.conversation_set.all().delete()
            instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfigView(GenericAPIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_CONFIGURE_MODELS

    @swagger_auto_schema(
        operation_description="Get catalog configuration",
        responses={
            200: openapi.Response(
                description="Catalog configuration",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "language_model_providers": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of available language model providers",
                        ),
                        "embedding_providers": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of available embedding providers",
                        ),
                    },
                ),
            )
        },
    )
    def get(self, request, *args, **kwargs):
        response_body = {
            "language_model_providers": [
                cls.NAME for cls in LanguageModelRegistry().get_provider_classes()
            ],
            "embedding_providers": [
                cls.NAME for cls in EmbeddingProviderRegistry().get_provider_classes()
            ],
        }

        return Response(response_body)


class ConfigLanguageModelView(GenericAPIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_CONFIGURE_MODELS

    @swagger_auto_schema(
        operation_description="Get available language models for a given provider",
        responses={
            200: openapi.Response(
                description="List of available language models",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                ),
            )
        },
    )
    def get(self, request, *args, **kwargs):
        provider_name = kwargs.get("provider_name")
        response_body = LanguageModelRegistry().provider_class_by_name(provider_name).available_models()

        return Response(response_body)


class ConfigEmbeddingModelView(GenericAPIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_CONFIGURE_MODELS

    @swagger_auto_schema(
        operation_description="Get available embedding models and vector size constraints for a given provider",
        responses={
            200: openapi.Response(
                description="Embedding models config",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "models": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description="List of available embedding model names",
                        ),
                        "vector_size_constraints": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description=(
                                "Map of model name to allowed vector sizes. "
                                "Empty object means no constraints."
                            ),
                            additional_properties=openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_INTEGER),
                            ),
                        ),
                    },
                ),
            )
        },
    )
    def get(self, request, *args, **kwargs):
        provider_name = kwargs.get("provider_name")
        provider_class = EmbeddingProviderRegistry().provider_class_by_name(provider_name)
        response_body = {
            "models": provider_class.available_models(),
            "vector_size_constraints": provider_class.vector_size_constraints(),
        }

        return Response(response_body)


def _resolve_dataset_role(codenames):
    """Return the DatasetRole name whose full permission set is covered by `codenames`, or None.

    `codenames` comes from guardian's `get_users_with_perms`/`get_groups_with_perms`
    (`attach_perms=True`), which report bare codenames (e.g. ``"access_dataset"``).
    """
    from account.models import DatasetRole

    bare_codenames = set(codenames)
    matches = []
    for role in DatasetRole.objects.prefetch_related("permissions"):
        role_codenames = {p.codename for p in role.permissions.all()}
        if role_codenames and role_codenames <= bare_codenames:
            matches.append((role.name, len(role_codenames)))
    if not matches:
        return None
    return max(matches, key=lambda pair: pair[1])[0]


class DataSetAccessListView(GenericAPIView):
    permission_classes = [IsApplicationAdmin]

    @swagger_auto_schema(operation_description="List access grants for a data set")
    def get(self, request, data_set_id):
        dataset = get_object_or_404(DataSet, pk=data_set_id)
        rows = []
        for user, codenames in get_users_with_perms(dataset, attach_perms=True, with_group_users=False).items():
            if user.is_service_account:
                # Service accounts get dataset access exclusively via their own "Data Sets"
                # field (CreateUpdateServiceAccountSerializer._sync_data_sets), which always
                # assigns "editor" and re-syncs on every save. Surfacing them here too would
                # let this screen set a different role that the next service-account save
                # would silently overwrite — two sources of truth for the same grant.
                continue
            rows.append(
                {
                    "target_type": "user",
                    "target_id": user.id,
                    "target_label": user.email,
                    "role": _resolve_dataset_role(codenames),
                }
            )
        for group, codenames in get_groups_with_perms(dataset, attach_perms=True).items():
            rows.append(
                {
                    "target_type": "group",
                    "target_id": group.id,
                    "target_label": group.name,
                    "role": _resolve_dataset_role(codenames),
                }
            )
        serializer = DataSetAccessSerializer(rows, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Grant a user or group a role on a data set",
        request_body=DataSetAccessGrantSerializer,
    )
    def post(self, request, data_set_id):
        dataset = get_object_or_404(DataSet, pk=data_set_id)
        serializer = DataSetAccessGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_model = User if serializer.validated_data["target_type"] == "user" else Group
        target = get_object_or_404(target_model, pk=serializer.validated_data["target_id"])
        remove_all_dataset_grants(target, dataset)
        assign_dataset_role(target, dataset, serializer.validated_data["role"])
        return Response(status=status.HTTP_201_CREATED)


class DataSetAccessDetailView(GenericAPIView):
    permission_classes = [IsApplicationAdmin]

    @swagger_auto_schema(operation_description="Revoke a user's or group's access to a data set")
    def delete(self, request, data_set_id, target_type, target_id):
        if target_type not in {"user", "group"}:
            return Response({"target_type": "Must be 'user' or 'group'."}, status=status.HTTP_400_BAD_REQUEST)
        dataset = get_object_or_404(DataSet, pk=data_set_id)
        target_model = User if target_type == "user" else Group
        target = get_object_or_404(target_model, pk=target_id)
        remove_all_dataset_grants(target, dataset)
        return Response(status=status.HTTP_204_NO_CONTENT)
