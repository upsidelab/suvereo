from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import User
from account.serializers import UserSerializer
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
        if self.request.user and self.request.user.is_staff:
            return DataSet.objects.all()

        return DataSet.objects.filter(users=self.request.user)

    @swagger_auto_schema(operation_description="Create a new data set", request_body=DataSetCreateSerializer)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            self.permission_denied(self.request)

        with transaction.atomic():
            preconfigure_agents = serializer.validated_data.pop("preconfigure_agents")
            data_set = serializer.save()
            data_set.users.add(self.request.user)
            if preconfigure_agents:
                AgentPreconfigurationService.preconfigure_available_agents(data_set)


class DataSetDetailView(RetrieveAPIView):
    serializer_class = DataSetSerializer
    permission_classes = [IsAdminUser]
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


class DataSetUserListView(ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="List users in a data set",
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return DataSet.objects.get(id=self.kwargs["data_set_id"]).users.all()

    @swagger_auto_schema(
        operation_description="Add a user to a data set",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"user_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the user")},
        ),
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, *args, **kwargs):
        user = User.objects.get(id=self.request.data["user_id"])
        DataSet.objects.get(id=self.kwargs["data_set_id"]).users.add(user)
        return Response({}, status=status.HTTP_201_CREATED)


class DataSetUserView(GenericAPIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Remove a user from a data set",
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter("user_id", openapi.IN_PATH, description="ID of the user", type=openapi.TYPE_INTEGER),
        ],
    )
    def delete(self, *args, **kwargs):
        DataSet.objects.get(id=self.kwargs["data_set_id"]).users.remove(self.kwargs["user_id"])
        return Response({}, status=status.HTTP_204_NO_CONTENT)


class ConfigView(GenericAPIView):
    permission_classes = [IsAdminUser]

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
    permission_classes = [IsAdminUser]

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
    permission_classes = [IsAdminUser]

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
