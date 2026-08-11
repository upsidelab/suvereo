from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import datasets_visible_to, has_any_dataset_access
from catalog.entities.registry import entity_registry


class EntityListView(APIView):
    """List the registered domain entities and the columns each table shows."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not has_any_dataset_access(request.user):
            self.permission_denied(request)

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
        data_set = get_object_or_404(datasets_visible_to(self.request.user), pk=self.kwargs["data_set_id"])
        return registration.model.objects.filter(dataset_id=data_set.id).order_by("id")
