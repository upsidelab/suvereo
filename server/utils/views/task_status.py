from typing import Any

from celery import states
from celery.result import AsyncResult
from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class TaskStatusView(APIView):
    permission_classes = [IsAuthenticated]
    task_type: str
    response_serializer_class: type

    def get(self, request: Request, task_id: str, *args: Any, **kwargs: Any) -> Response:
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

    def _is_result_visible(self, user: AbstractBaseUser, result: Any) -> bool:
        raise NotImplementedError
