from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import (
    PERMISSIONS,
    any_permission_on_any_dataset_required,
    enforce_dataset_scoped_permission,
)
from agent.core.agents.selectable_tool_providing_integrations import SelectableToolProvidingIntegrations
from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.filters import AgentFilter
from agent.models.agent import Agent
from agent.serializers.configuration import (
    AgentListSerializer,
    AgentSerializer,
    AvailableAgentsResponseSerializer,
    ToolProvidingIntegrationOptionSerializer,
    agent_type_config_schema,
)
from agent.services import AgentVerificationService
from catalog.models import DataSet, Integration


class AgentTypesView(APIView):
    permission_classes = [IsAuthenticated]

    """View to get available agents."""

    @swagger_auto_schema(
        operation_description="Get available Agents", responses={200: AvailableAgentsResponseSerializer()}
    )
    @any_permission_on_any_dataset_required(PERMISSIONS.AGENT.ADD, PERMISSIONS.AGENT.CHANGE)
    def get(self, request: Request) -> Response:
        agent_registry = AgentRegistry()
        choices = [
            {
                "name": agent_class.NAME,
                "key": agent_class.AGENT_KEY,
                **agent_type_config_schema(agent_class),
            }
            for agent_class in agent_registry.get_plugin_classes()
        ]
        response_serializer = AvailableAgentsResponseSerializer(data={"choices": choices})
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AgentView(APIView):
    permission_classes = [IsAuthenticated]
    """View to get/create agents"""

    @swagger_auto_schema(
        operation_description="List all agents for a dataset",
        manual_parameters=[
            openapi.Parameter(
                "dataset",
                openapi.IN_QUERY,
                description="ID of the dataset",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
        responses={200: AgentListSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        filterset = AgentFilter(request.GET, queryset=Agent.objects.order_by("created_at"))
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_object_or_404(DataSet, pk=filterset.form.cleaned_data["dataset"])
        enforce_dataset_scoped_permission(self, PERMISSIONS.AGENT.VIEW, dataset)

        agents = list(filterset.qs)
        AgentVerificationService().verify(agents)
        if not request.user.is_superuser:
            agents = [agent for agent in agents if not agent.corrupted]

        serializer = AgentListSerializer(agents, many=True)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_description="Create a new agent.",
        request_body=AgentSerializer,
        responses={201: AgentSerializer()},
    )
    def post(self, request: Request) -> Response:
        try:
            dataset = DataSet.objects.get(pk=request.data.get("dataset"))
        except (DataSet.DoesNotExist, ValueError, TypeError):
            return Response({"dataset": ["Invalid data set."]}, status=status.HTTP_400_BAD_REQUEST)
        enforce_dataset_scoped_permission(self, PERMISSIONS.AGENT.ADD, dataset)

        serializer = AgentSerializer(data=request.data, context={"data_set_id": dataset.id})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(AgentSerializer(instance).data, status=status.HTTP_201_CREATED)


class AgentDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    """View to get manage agents"""

    @swagger_auto_schema(operation_description="Get a single configuration by id.", responses={200: AgentSerializer()})
    def get(self, request: Request, pk: int) -> Response:
        instance = get_object_or_404(Agent, pk=pk)
        enforce_dataset_scoped_permission(self, PERMISSIONS.AGENT.VIEW, instance.dataset, obscured_model=Agent)

        serializer = AgentSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Update an existing configuration by id.",
        request_body=AgentSerializer,
        responses={200: AgentSerializer()},
    )
    def put(self, request: Request, pk: int | None = None) -> Response:
        instance = get_object_or_404(Agent, pk=pk)
        enforce_dataset_scoped_permission(self, PERMISSIONS.AGENT.CHANGE, instance.dataset, obscured_model=Agent)

        serializer = AgentSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(corrupted=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Delete a configuration by id.", responses={204: "No Content", 404: "Not Found"}
    )
    def delete(self, request: Request, pk: int | None = None) -> Response:
        instance = get_object_or_404(Agent, pk=pk)
        enforce_dataset_scoped_permission(self, PERMISSIONS.AGENT.DELETE, instance.dataset, obscured_model=Agent)

        instance.set_deleted_at()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SelectableToolProvidingIntegrationsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List the data set's tool-providing integrations, which an agent can select.",
        manual_parameters=[
            openapi.Parameter(
                "dataset", openapi.IN_QUERY, description="ID of the dataset", type=openapi.TYPE_INTEGER, required=True
            )
        ],
        responses={200: ToolProvidingIntegrationOptionSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        dataset_id = request.query_params.get("dataset", "")
        if not dataset_id.isdigit():
            return Response({"dataset": ["A data set id is required."]}, status=status.HTTP_400_BAD_REQUEST)

        dataset = get_object_or_404(DataSet, pk=int(dataset_id))
        enforce_dataset_scoped_permission(self, PERMISSIONS.AGENT.VIEW, dataset)

        ids = SelectableToolProvidingIntegrations.ids(dataset.id)
        integrations = Integration.objects.filter(id__in=ids).order_by("id")
        return Response(
            ToolProvidingIntegrationOptionSerializer(integrations, many=True).data, status=status.HTTP_200_OK
        )
