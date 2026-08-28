from django.urls import path

from . import views

urlpatterns = [
    path("api/data_sets", views.DataSetListView.as_view(), name="data_set_list"),
    path("api/data_sets/<int:data_set_id>", views.DataSetDetailView.as_view(), name="data_set_detail"),
    path("api/config", views.ConfigView.as_view(), name="config"),
    path(
        "api/config/language_model_providers/<str:provider_name>",
        views.ConfigLanguageModelView.as_view(),
        name="config_language_model_provider",
    ),
    path(
        "api/config/embedding_providers/<str:provider_name>",
        views.ConfigEmbeddingModelView.as_view(),
        name="config_embedding_provider",
    ),
]
