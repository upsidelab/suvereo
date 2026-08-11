from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.authorization import (
    PERMISSIONS,
    any_global_permission_required,
    datasets_visible_to,
    global_permission_required,
)
from agent.core.registries.embeddings import EmbeddingProviderRegistry
from agent.core.registries.language_models import LanguageModelRegistry
from agent.models import AgenticExecution, Message
from agent.models.conversation import ConversationFile
from agent.services import AgentPreconfigurationService

from .models import DataSet
from .serializers import DataSetCreateSerializer, DataSetSerializer


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
        return datasets_visible_to(self.request.user)

    @swagger_auto_schema(operation_description="Create a new data set", request_body=DataSetCreateSerializer)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    @global_permission_required(PERMISSIONS.DATASET.ADD)
    def perform_create(self, serializer):
        with transaction.atomic():
            preconfigure_agents = serializer.validated_data.pop("preconfigure_agents")
            data_set = serializer.save()
            if preconfigure_agents:
                AgentPreconfigurationService.preconfigure_available_agents(data_set)


class DataSetDetailView(RetrieveAPIView):
    serializer_class = DataSetSerializer
    permission_classes = [IsAuthenticated]
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
        instance = get_object_or_404(datasets_visible_to(request.user), pk=kwargs[self.lookup_url_kwarg])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Update a data set (embedding fields are ignored)",
        request_body=DataSetSerializer,
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
            )
        ],
    )
    @global_permission_required(PERMISSIONS.DATASET.CHANGE)
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
    @global_permission_required(PERMISSIONS.DATASET.DELETE)
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
    permission_classes = [IsAuthenticated]

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
    @any_global_permission_required(PERMISSIONS.DATASET.ADD, PERMISSIONS.DATASET.CHANGE)
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
    permission_classes = [IsAuthenticated]

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
    @any_global_permission_required(PERMISSIONS.DATASET.ADD, PERMISSIONS.DATASET.CHANGE)
    def get(self, request, *args, **kwargs):
        provider_name = kwargs.get("provider_name")
        response_body = LanguageModelRegistry().provider_class_by_name(provider_name).available_models()

        return Response(response_body)


class ConfigEmbeddingModelView(GenericAPIView):
    permission_classes = [IsAuthenticated]

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
    @any_global_permission_required(PERMISSIONS.DATASET.ADD, PERMISSIONS.DATASET.CHANGE)
    def get(self, request, *args, **kwargs):
        provider_name = kwargs.get("provider_name")
        provider_class = EmbeddingProviderRegistry().provider_class_by_name(provider_name)
        response_body = {
            "models": provider_class.available_models(),
            "vector_size_constraints": provider_class.vector_size_constraints(),
        }

        return Response(response_body)
