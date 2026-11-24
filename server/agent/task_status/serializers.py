from rest_framework import serializers

from agent.conversation.tasks import TaskStatus


class UploadedFileResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    filename = serializers.CharField()
    file_url = serializers.CharField()
    content_type = serializers.CharField(required=False, allow_null=True)


class FileUploadTaskResultSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    conversation_id = serializers.IntegerField(required=False)
    file_id = serializers.IntegerField(required=False)
    uploaded_file = UploadedFileResultSerializer(required=False)
    error = serializers.CharField(required=False)


class FileUploadTaskStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=TaskStatus)
    result = FileUploadTaskResultSerializer(required=False)


class MessagePushTaskResultSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False)
    message_id = serializers.IntegerField(required=False)
    error = serializers.CharField(required=False)


class MessagePushTaskStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=TaskStatus)
    result = MessagePushTaskResultSerializer(required=False)
