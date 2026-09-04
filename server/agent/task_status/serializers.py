from rest_framework import serializers


class UploadedFileResultSerializer(serializers.Serializer):
    """Shape of the `uploaded_file` entry in a file upload task's result."""

    id = serializers.IntegerField()
    filename = serializers.CharField()
    file_url = serializers.CharField()
    content_type = serializers.CharField(required=False, allow_null=True)


class FileUploadTaskResultSerializer(serializers.Serializer):
    """Explicit shape of a file upload task's result, once it has finished running."""

    status = serializers.CharField(required=False)
    conversation_id = serializers.IntegerField(required=False)
    file_id = serializers.IntegerField(required=False)
    uploaded_file = UploadedFileResultSerializer(required=False)
    error = serializers.CharField(required=False)


class FileUploadTaskStatusSerializer(serializers.Serializer):
    """Response of the file-upload-status endpoint."""

    task_id = serializers.CharField()
    status = serializers.CharField()
    result = FileUploadTaskResultSerializer(required=False)


class MessagePushTaskResultSerializer(serializers.Serializer):
    """Explicit shape of a message push task's result, once it has finished running."""

    conversation_id = serializers.IntegerField(required=False)
    message_id = serializers.IntegerField(required=False)
    error = serializers.CharField(required=False)


class MessagePushTaskStatusSerializer(serializers.Serializer):
    """Response of the message-push-status endpoint."""

    task_id = serializers.CharField()
    status = serializers.CharField()
    result = MessagePushTaskResultSerializer(required=False)
