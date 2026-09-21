from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, any_permission_on_any_dataset_required, enforce_dataset_scoped_permission
from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.integrations.tasks import sync_integration_task
from catalog.models import DataSet, Integration
from catalog.models.integration import UNIQUE_INTEGRATION_TYPE_CONSTRAINT
from catalog.serializers import IntegrationSerializer, IntegrationTypeSerializer, IntegrationUpdateSerializer


class IntegrationTypeListView(APIView):
    """List the registered integration types and the config form each one expects."""

    permission_classes = [IsAuthenticated]

    @any_permission_on_any_dataset_required(PERMISSIONS.INTEGRATION.ADD, PERMISSIONS.INTEGRATION.CHANGE)
    def get(self, request):
        types = [
            {
                "type": cls.TYPE,
                "name": cls.NAME,
                "integration_type_name": cls.INTEGRATION_TYPE_NAME,
                "syncable": cls.is_syncable(),
                "config_schema": cls().get_config_schema(),
            }
            for cls in IntegrationPluginRegistry().get_plugin_classes()
        ]
        return Response(IntegrationTypeSerializer(types, many=True).data)


class _DataSetScopedView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_dataset(self, data_set_id):
        return get_object_or_404(DataSet, pk=data_set_id)

    def _get_integration(self, data_set_id, pk):
        return get_object_or_404(Integration, pk=pk, dataset_id=data_set_id)


class IntegrationListView(_DataSetScopedView):
    def get(self, request, data_set_id):
        data_set = self._get_dataset(data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.VIEW, data_set)
        qs = Integration.objects.filter(dataset_id=data_set_id).order_by("type", "id")
        return Response(IntegrationSerializer(qs, many=True).data)

    def post(self, request, data_set_id):
        data_set = self._get_dataset(data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.ADD, data_set)

        serializer = IntegrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        integration_type = serializer.validated_data["type"]

        try:
            plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration_type)
        except KeyError:
            return Response(
                {"detail": f"No integration plugin registered with TYPE='{integration_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                integration = serializer.save(
                    dataset=data_set, allows_multiple_instances=plugin_class.ALLOWS_MULTIPLE_INSTANCES
                )
        except IntegrityError as e:
            # Only the uniqueness constraint means "already configured"; anything else is a real
            # database failure and must not be reported to the admin as a duplicate.
            if UNIQUE_INTEGRATION_TYPE_CONSTRAINT not in str(e):
                raise
            return Response(
                {"detail": f"This dataset already has a '{integration_type}' integration."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(IntegrationSerializer(integration).data, status=status.HTTP_201_CREATED)


class IntegrationSyncView(_DataSetScopedView):
    def post(self, request, data_set_id, pk):
        data_set = self._get_dataset(data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.SYNC, data_set)
        integration = self._get_integration(data_set_id, pk)
        task = sync_integration_task.delay(integration.id)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class IntegrationUpdateDeleteView(_DataSetScopedView):
    def patch(self, request, data_set_id, pk):
        data_set = self._get_dataset(data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.CHANGE, data_set)
        integration = self._get_integration(data_set_id, pk)
        serializer = IntegrationUpdateSerializer(integration, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(IntegrationSerializer(integration).data)

    def delete(self, request, data_set_id, pk):
        data_set = self._get_dataset(data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.DELETE, data_set)
        integration = self._get_integration(data_set_id, pk)
        integration.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
