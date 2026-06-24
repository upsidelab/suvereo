from django.urls import path

from .views import EntityListView, EntityRecordsView

urlpatterns = [
    path("api/entities/", EntityListView.as_view(), name="entity-list"),
    path("api/datasets/<int:data_set_id>/<slug:slug>/", EntityRecordsView.as_view(), name="entity-records"),
]
