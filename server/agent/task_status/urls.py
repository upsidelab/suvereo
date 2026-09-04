from django.urls import path

from .views import FileUploadStatusView, MessagePushStatusView

urlpatterns = [
    path("api/file-upload-status/<str:task_id>/", FileUploadStatusView.as_view(), name="file-upload-status"),
    path("api/message-push-status/<str:task_id>/", MessagePushStatusView.as_view(), name="message-push-status"),
]
