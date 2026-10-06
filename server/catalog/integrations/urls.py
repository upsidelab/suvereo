from django.urls import path

from .oauth import (
    IntegrationOAuthCallbackView,
    IntegrationOAuthRefreshView,
    IntegrationOAuthResultView,
    IntegrationOAuthStartView,
)
from .views import (
    IntegrationListView,
    IntegrationSyncView,
    IntegrationTypeListView,
    IntegrationUpdateDeleteView,
)

urlpatterns = [
    path("api/integration-types/", IntegrationTypeListView.as_view(), name="integration-types"),
    path(
        "api/data_sets/<int:data_set_id>/integrations/oauth/start/",
        IntegrationOAuthStartView.as_view(),
        name="integration-oauth-start",
    ),
    path(
        "api/data_sets/<int:data_set_id>/integrations/oauth/refresh/",
        IntegrationOAuthRefreshView.as_view(),
        name="integration-oauth-refresh",
    ),
    path(
        "api/integrations/oauth/callback/",
        IntegrationOAuthCallbackView.as_view(),
        name="integration-oauth-callback",
    ),
    path(
        "api/integrations/oauth/result/",
        IntegrationOAuthResultView.as_view(),
        name="integration-oauth-result",
    ),
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
