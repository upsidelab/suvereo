from celery import Task, shared_task
from enthusiast_common.agentic_execution import ExecutionFailureCode

from agent.agentic_execution.conversation import ExecutionConversation
from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.agentic_execution.runner import AgenticExecutionRunner
from agent.models.agentic_execution import AgenticExecution


class MarkExecutionFailedOnErrorTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        execution_id = args[0] if args else kwargs.get("execution_id")
        if execution_id is None:
            return
        try:
            AgenticExecution.objects.get(pk=execution_id).mark_failed(
                failure_code=ExecutionFailureCode.RUNTIME_ERROR,
                failure_explanation=f"{type(exc).__name__}: {exc}",
            )
        except AgenticExecution.DoesNotExist:
            pass


@shared_task(base=MarkExecutionFailedOnErrorTask, max_retries=0)
def run_agentic_execution_task(execution_id: int):
    execution = AgenticExecution.objects.select_related("agent", "conversation__agent").get(pk=execution_id)
    execution.mark_in_progress()

    definition = AgenticExecutionDefinitionRegistry().get_by_key(execution.execution_key)
    result = AgenticExecutionRunner().run(
        execution.execution_key, execution.input, ExecutionConversation(execution.conversation, definition)
    )

    if result.success:
        execution.mark_finished(result.output)
    else:
        execution.mark_failed(
            failure_code=result.failure_code or ExecutionFailureCode.UNKNOWN,
            failure_explanation=result.failure_summary,
        )
