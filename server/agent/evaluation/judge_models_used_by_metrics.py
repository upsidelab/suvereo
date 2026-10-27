from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricError, MetricRegistry
from enthusiast_common.evaluation.metrics.llm import JudgePromptParams
from enthusiast_common.evaluation.suite import ModelTarget

from agent.evaluation.user_model_in_use import has_user_goals


def judge_models_used_by_metrics(loaded: LoadedSuite) -> list[ModelTarget]:
    """The judge models a suite's LLM metrics will ask, each once: a metric's own `judge`, else the suite's `judge`.

    Builds every metric to read its params; one that cannot be built is skipped (SuiteLoader and RunScorer report it).
    A suite judge no LLM metric relies on is left out, unless a simulated user's goal needs it (goal_reached).
    """
    registry = MetricRegistry()
    configs = [*loaded.suite.metrics, *(c for case in loaded.cases for c in loaded.suite.metrics_for(case))]
    models: dict[tuple[str, str], ModelTarget] = {}
    for config in configs:
        try:
            params = registry.build_metric(config, loaded.base_dir).params
        except MetricError:
            continue
        if not isinstance(params, JudgePromptParams):
            continue
        model = params.judge or loaded.suite.judge
        if model is not None:
            models.setdefault((model.provider, model.model), model)
    if has_user_goals(loaded) and loaded.suite.judge is not None:
        judge = loaded.suite.judge
        models.setdefault((judge.provider, judge.model), judge)
    return list(models.values())
