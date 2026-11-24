from rest_framework import serializers

from agent.conversation.tasks import TaskStatus


class IntegrationSyncTaskResultSerializer(serializers.Serializer):
    integration_id = serializers.IntegerField(required=False)
    data_set_id = serializers.IntegerField(required=False)
    synced = serializers.BooleanField(required=False)
    error = serializers.CharField(required=False)


class IntegrationSyncTaskStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=TaskStatus)
    result = IntegrationSyncTaskResultSerializer(required=False)
