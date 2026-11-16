from celery import states
from celery.result import AsyncResult
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class TaskStatusView(APIView):
    """
    Base view to check the status of an enqueued task running in the background.

    Only reports on tasks of `task_type` (subclasses must set it) - a task_id belonging to a
    different job, or to no job we recognise, is reported as PENDING rather than 404, matching
    Celery's own behaviour for unknown ids and avoiding confirming or denying its existence.
    Once the task has succeeded, the result is only revealed to a requester allowed to see
    the resource it belongs to (subclasses implement `_is_result_visible`) - anyone else also sees PENDING.
    """

    permission_classes = [IsAuthenticated]
    task_type: str
    response_serializer_class: type

    def get(self, request, task_id, *args, **kwargs):
        try:
            task_result = AsyncResult(task_id)

            response_data = {
                "task_id": task_id,
                "status": task_result.status,
            }

            if task_result.status == states.SUCCESS:
                result = task_result.result
                if self._is_result_visible(request.user, result):
                    response_data["result"] = result
                else:
                    response_data["status"] = states.PENDING
            elif task_result.status == states.FAILURE:
                response_data["result"] = {"error": str(task_result.result)}

            serializer = self.response_serializer_class(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to get task status: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _is_result_visible(self, user, result) -> bool:
        raise NotImplementedError
