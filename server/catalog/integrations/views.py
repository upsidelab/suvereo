from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.integrations.tasks import sync_integration_task
from catalog.models import DataSet, Integration
from catalog.serializers import IntegrationSerializer, IntegrationTypeSerializer, IntegrationUpdateSerializer


class IntegrationTypeListView(APIView):
    """List the registered integration types and the config form each one expects."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        types = [
            {"type": cls.TYPE, "name": cls.NAME, "config_schema": cls().get_config_schema()}
            for cls in IntegrationPluginRegistry().get_plugin_classes()
        ]
        return Response(IntegrationTypeSerializer(types, many=True).data)


class _DataSetScopedView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_dataset(self, request, data_set_id):
        data_set = get_object_or_404(DataSet, pk=data_set_id)
        if not request.user.has_dataset_access(data_set):
            raise PermissionDenied("No dataset access.")
        return data_set

    def _get_integration(self, data_set_id, pk):
        return get_object_or_404(Integration, pk=pk, dataset_id=data_set_id)


class IntegrationListView(_DataSetScopedView):
    def get(self, request, data_set_id):
        self._get_dataset(request, data_set_id)
        qs = Integration.objects.filter(dataset_id=data_set_id).order_by("type")
        return Response(IntegrationSerializer(qs, many=True).data)

    def post(self, request, data_set_id):
        data_set = self._get_dataset(request, data_set_id)

        serializer = IntegrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        integration_type = serializer.validated_data["type"]

        try:
            IntegrationPluginRegistry().get_plugin_class_by_type(integration_type)
        except KeyError:
            return Response(
                {"detail": f"No integration plugin registered with TYPE='{integration_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Integration.objects.filter(dataset=data_set, type=integration_type).exists():
            return Response(
                {"detail": f"This dataset already has a '{integration_type}' integration."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        integration = serializer.save(dataset=data_set)
        sync_integration_task.delay(integration.id)
        return Response(IntegrationSerializer(integration).data, status=status.HTTP_201_CREATED)


class IntegrationSyncView(_DataSetScopedView):
    def post(self, request, data_set_id, pk):
        self._get_dataset(request, data_set_id)
        integration = self._get_integration(data_set_id, pk)
        task = sync_integration_task.delay(integration.id)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class IntegrationUpdateDeleteView(_DataSetScopedView):
    def patch(self, request, data_set_id, pk):
        self._get_dataset(request, data_set_id)
        integration = self._get_integration(data_set_id, pk)
        serializer = IntegrationUpdateSerializer(integration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(IntegrationSerializer(integration).data)

    def delete(self, request, data_set_id, pk):
        self._get_dataset(request, data_set_id)
        integration = self._get_integration(data_set_id, pk)
        integration.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
