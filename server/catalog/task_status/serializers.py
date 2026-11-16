from rest_framework import serializers

from agent.conversation.tasks import TaskStatus


class IntegrationSyncTaskResultSerializer(serializers.Serializer):
    """Explicit shape of an integration sync task's result, once it has finished running."""

    integration_id = serializers.IntegerField(required=False)
    data_set_id = serializers.IntegerField(required=False)
    synced = serializers.BooleanField(required=False)
    error = serializers.CharField(required=False)


class IntegrationSyncTaskStatusSerializer(serializers.Serializer):
    """Response of the integration-sync-status endpoint."""

    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=TaskStatus)
    result = IntegrationSyncTaskResultSerializer(required=False)
