from django.urls import include, path

from . import views

urlpatterns = (
    path("", include("agent.conversation.urls")),
    path("api/agents", views.AgentView.as_view(), name="agents"),
    path("api/agents/<int:pk>", views.AgentDetailsView.as_view(), name="agent-details"),
    path("api/agents/types", views.AgentTypesView.as_view(), name="agent-types"),
    path(
        "api/agents/tool-providing-integrations",
        views.SelectableToolProvidingIntegrationsView.as_view(),
        name="agent-tool-providing-integrations",
    ),
)
