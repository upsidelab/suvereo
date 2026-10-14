from pathlib import Path

from enthusiast_common.agentic_execution import BaseAgenticExecutionDefinition
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricError, MetricRegistry
from enthusiast_common.evaluation.metrics.auto import AUTO_METRICS
from enthusiast_common.evaluation.metrics.llm import JudgePromptParams
from enthusiast_common.evaluation.mocks.errors import MockError
from enthusiast_common.evaluation.suite import EvalSuite
from enthusiast_common.evaluation.suite_reader import SuiteReader
from pydantic import ValidationError

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.aggregation import DERIVED_METRICS, TAG_PREFIX
from agent.evaluation.integrations import MockIntegrationFactory
from agent.evaluation.judge_models_used_by_metrics import judge_models_used_by_metrics
from agent.evaluation.runner.case_runner import JUDGE_COST
from agent.models import Agent

RESERVED_METRIC_NAMES = {metric.NAME for metric in AUTO_METRICS} | {JUDGE_COST} | set(DERIVED_METRICS)


class SuiteLoader:
    """Reads a suite and checks what needs the host, so a mistake fails before any tokens are spent."""

    def load(self, path: Path) -> LoadedSuite:
        """The suite with its execution key resolved; raises EvalSuiteError naming the first problem found."""
        loaded = SuiteReader().read(path)
        execution = self._resolve_execution(loaded.suite)
        self._check_prompt_files(loaded)
        self._check_metrics(loaded)
        self._check_models(loaded)
        self._check_integrations(loaded)
        self._check_inputs(loaded, execution)
        suite = loaded.suite.model_copy(update={"execution_key": execution.EXECUTION_KEY})
        return loaded.model_copy(update={"suite": suite})

    def _resolve_execution(self, suite: EvalSuite) -> type[BaseAgenticExecutionDefinition]:
        agent_type = suite.agent.type or self._existing_agent_type(suite.agent.id)
        definitions = AgenticExecutionDefinitionRegistry().get_by_agent_type(agent_type)
        if suite.execution_key:
            definitions = [d for d in definitions if d.EXECUTION_KEY == suite.execution_key]
            if not definitions:
                raise EvalSuiteError(f"Agent type '{agent_type}' has no execution '{suite.execution_key}'.")
        if len(definitions) != 1:
            raise EvalSuiteError(
                f"Agent type '{agent_type}' has {len(definitions)} registered executions; set 'execution_key'."
            )
        return definitions[0]

    @staticmethod
    def _existing_agent_type(agent_id: int) -> str:
        agent_type = Agent.objects.filter(pk=agent_id).values_list("agent_type", flat=True).first()
        if agent_type is None:
            raise EvalSuiteError(f"There is no agent with id {agent_id}.")
        return agent_type

    @staticmethod
    def _check_models(loaded: LoadedSuite) -> None:
        """Models under test and every judge model, metric-level ones included, need a known provider."""
        registry = LanguageModelRegistry()
        for target in [*loaded.suite.models, *judge_models_used_by_metrics(loaded)]:
            try:
                registry.provider_class_by_name(target.provider)
            except KeyError:
                raise EvalSuiteError(f"Unknown language model provider '{target.provider}'.") from None

    @staticmethod
    def _check_prompt_files(loaded: LoadedSuite) -> None:
        for variant in loaded.suite.variants:
            if variant.system_prompt_file and not (loaded.base_dir / variant.system_prompt_file).is_file():
                raise EvalSuiteError(f"Variant '{variant.name}': no prompt file {variant.system_prompt_file}.")

    @staticmethod
    def _check_metrics(loaded: LoadedSuite) -> None:
        """Every metric builds, has a usable name, a judge if it needs one, and an aggregate fitting its value type;
        a case's override keeps its suite metric's value type and aggregate, as results are aggregated across cases."""
        registry = MetricRegistry()
        first_seen: dict[str, tuple[str, str | None]] = {}
        for config in loaded.suite.metrics:
            try:
                first_seen[config.name] = (registry.metric_class(config.type).VALUE_TYPE, config.aggregate)
            except MetricError:
                continue
        for case in loaded.cases:
            for config in loaded.suite.metrics_for(case):
                if config.name in RESERVED_METRIC_NAMES:
                    raise EvalSuiteError(
                        f"Metric name '{config.name}' is reserved for a built-in figure; pick another."
                    )
                if "." in config.name or config.name.startswith(TAG_PREFIX):
                    raise EvalSuiteError(
                        f"Metric name '{config.name}' may not contain '.' or start with '{TAG_PREFIX}'; reports use "
                        "them for components and tags."
                    )
                try:
                    metric = registry.build_metric(config, loaded.base_dir)
                except MetricError as e:
                    raise EvalSuiteError(f"Case '{case.id}': {e}") from e
                params = metric.params
                if isinstance(params, JudgePromptParams) and params.judge is None and loaded.suite.judge is None:
                    raise EvalSuiteError(
                        f"Metric '{config.name}' needs a judge model; set 'judge' in the suite or in its params."
                    )
                if config.aggregate == "distribution" and metric.VALUE_TYPE != "label":
                    raise EvalSuiteError(f"Metric '{config.name}': aggregate 'distribution' is only for label metrics.")
                if metric.VALUE_TYPE == "label" and config.aggregate not in (None, "distribution"):
                    raise EvalSuiteError(
                        f"Metric '{config.name}' is a label metric; its only aggregate is distribution."
                    )
                shape = (metric.VALUE_TYPE, config.aggregate)
                if first_seen.setdefault(config.name, shape) != shape:
                    raise EvalSuiteError(
                        f"Case '{case.id}': metric '{config.name}' must keep the value type and aggregate it has "
                        "elsewhere in the suite, as its results are aggregated together."
                    )

    @staticmethod
    def _check_integrations(loaded: LoadedSuite) -> None:
        factory = MockIntegrationFactory(loaded.base_dir)
        for case in loaded.cases:
            for config in loaded.suite.integrations_for(case):
                integration = factory.build(config)
                try:
                    for mock_class in integration.mock_classes():
                        integration.mock_for(mock_class)
                except (MockError, OSError, ValueError) as e:
                    raise EvalSuiteError(f"Case '{case.id}', integration {config.key}: {e}") from e

    @staticmethod
    def _check_inputs(loaded: LoadedSuite, execution: type[BaseAgenticExecutionDefinition]) -> None:
        for case in loaded.cases:
            try:
                execution.INPUT_TYPE(**case.input)
            except ValidationError as e:
                raise EvalSuiteError(f"Case '{case.id}': invalid input: {e}") from e
