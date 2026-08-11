from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import is_dataset_member
from catalog.entities.registry import entity_registry
from catalog.models import DataSet


class EntityListView(APIView):
    """List the registered domain entities and the columns each table shows."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = [
            {
                "slug": registration.slug,
                "label": registration.label,
                "fields": [{"name": f.name, "label": f.label or f.name} for f in registration.fields],
            }
            for registration in entity_registry.all()
        ]
        return Response(data)


class EntityRecordsView(ListAPIView):
    """Read-only, paginated list of one entity's records within a DataSet."""

    permission_classes = [IsAuthenticated]

    def _registration(self):
        registration = entity_registry.get(self.kwargs["slug"])
        if registration is None:
            raise Http404("Unknown entity.")
        return registration

    def get_serializer_class(self):
        return self._registration().serializer

    def get_queryset(self):
        registration = self._registration()
        data_set = get_object_or_404(DataSet, pk=self.kwargs["data_set_id"])
        if not is_dataset_member(self.request.user, data_set):
            raise self.permission_denied(self.request)
        return registration.model.objects.filter(dataset_id=self.kwargs["data_set_id"]).order_by("id")
