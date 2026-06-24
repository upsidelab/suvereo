from django.urls import path

from .views import (
    IntegrationListView,
    IntegrationSyncView,
    IntegrationTestConnectionView,
    IntegrationTypeListView,
)

urlpatterns = [
    path("api/integration-types/", IntegrationTypeListView.as_view(), name="integration-types"),
    path("api/data_sets/<int:data_set_id>/integrations/", IntegrationListView.as_view(), name="integration-list"),
    path(
        "api/data_sets/<int:data_set_id>/integrations/<int:pk>/sync/",
        IntegrationSyncView.as_view(),
        name="integration-sync",
    ),
    path(
        "api/data_sets/<int:data_set_id>/integrations/<int:pk>/test-connection/",
        IntegrationTestConnectionView.as_view(),
        name="integration-test-connection",
    ),
]
