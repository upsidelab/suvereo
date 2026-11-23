from django.urls import path

from catalog.task_status.views import IntegrationSyncStatusView

urlpatterns = [
    path(
        "api/integration-sync-status/<str:task_id>/",
        IntegrationSyncStatusView.as_view(),
        name="integration-sync-status",
    ),
]
