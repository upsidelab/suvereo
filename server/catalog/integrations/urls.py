from django.urls import path

from .views import (
    IntegrationListView,
    IntegrationSyncView,
    IntegrationTypeListView,
    IntegrationUpdateDeleteView,
)

urlpatterns = [
    path("api/integration-types/", IntegrationTypeListView.as_view(), name="integration-types"),
    path("api/data_sets/<int:data_set_id>/integrations/", IntegrationListView.as_view(), name="integration-list"),
    path(
        "api/data_sets/<int:data_set_id>/integrations/<int:pk>/",
        IntegrationUpdateDeleteView.as_view(),
        name="integration-detail",
    ),
    path(
        "api/data_sets/<int:data_set_id>/integrations/<int:pk>/sync/",
        IntegrationSyncView.as_view(),
        name="integration-sync",
    ),
]
