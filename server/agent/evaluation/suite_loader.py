from pathlib import Path

from pydantic import ValidationError
from suvereo_common.agentic_execution import BaseAgenticExecutionDefinition
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.metrics import MetricError, MetricRegistry
from suvereo_common.evaluation.metrics.auto import auto_metrics_for
from suvereo_common.evaluation.metrics.llm import JudgePromptParams
from suvereo_common.evaluation.mocks.errors import MockError
from suvereo_common.evaluation.suite import AgenticExecutionEvalCase, ConversationEvalCase, EvalSuite, SuiteKind
from suvereo_common.evaluation.suite_reader import SuiteReader

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.core.registries.agents.agent_registry import AgentRegistry, AgentRegistryError
from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.aggregation import DERIVED_METRICS
from agent.evaluation.integrations import MockIntegrationFactory
from agent.evaluation.judge_models_used_by_metrics import judge_models_used_by_metrics
from agent.evaluation.runner.case_runner import JUDGE_COST, USER_COST
from agent.evaluation.suite_selection import SuiteSelection
from agent.evaluation.user_model_in_use import user_model_in_use
from agent.evaluation.user_simulator_registry import UserSimulatorRegistry
from agent.models import Agent


def reserved_metric_names(kind: SuiteKind) -> set[str]:
    costs = {JUDGE_COST, USER_COST} if kind == SuiteKind.CONVERSATION else {JUDGE_COST}
    return {metric.NAME for metric in auto_metrics_for(kind)} | costs | set(DERIVED_METRICS)


class SuiteLoader:
    def load(self, path: Path, selection: SuiteSelection | None = None) -> LoadedSuite:
        loaded = SuiteReader().read(path)
        if selection is not None:
            loaded = selection.apply(loaded)
        agent_type = loaded.suite.agent.type or self._existing_agent_type(loaded.suite.agent.id)
        kind = self._resolve_kind(loaded.suite, agent_type)
        execution = self._resolve_execution(loaded.suite, agent_type) if kind == SuiteKind.EXECUTION else None
        if execution is None and loaded.suite.execution_key:
            raise EvalSuiteError("'execution_key' is for execution suites; this is a conversation suite.")
        self._check_sandbox_agent_type(loaded.suite)
        self._check_prompt_files(loaded)
        self._check_metrics(loaded, kind)
        self._check_models(loaded)
        self._check_integrations(loaded)
        if execution is not None:
            self._check_inputs(loaded, execution)
        else:
            self._check_conversation_cases(loaded, agent_type)
        execution_key = execution.EXECUTION_KEY if execution is not None else None
        suite = loaded.suite.model_copy(update={"kind": kind, "execution_key": execution_key})
        return loaded.model_copy(update={"suite": suite})

    @staticmethod
    def _resolve_kind(suite: EvalSuite, agent_type: str) -> SuiteKind:
        if suite.kind is not None:
            return suite.kind
        if suite.execution_key:
            return SuiteKind.EXECUTION
        if AgenticExecutionDefinitionRegistry().get_by_agent_type(agent_type):
            return SuiteKind.EXECUTION
        return SuiteKind.CONVERSATION

    @staticmethod
    def _resolve_execution(suite: EvalSuite, agent_type: str) -> type[BaseAgenticExecutionDefinition]:
        definitions = AgenticExecutionDefinitionRegistry().get_by_agent_type(agent_type)
        if suite.execution_key:
            definitions = [d for d in definitions if suite.execution_key == d.EXECUTION_KEY]
            if not definitions:
                raise EvalSuiteError(f"Agent type '{agent_type}' has no execution '{suite.execution_key}'.")
        if len(definitions) != 1:
            raise EvalSuiteError(
                f"Agent type '{agent_type}' has {len(definitions)} registered executions; set 'execution_key'."
            )
        return definitions[0]

    @staticmethod
    def _check_sandbox_agent_type(suite: EvalSuite) -> None:
        if not suite.agent.is_sandbox:
            return
        try:
            AgentRegistry().get_agent_class_by_type(suite.agent.type)
        except AgentRegistryError as e:
            raise EvalSuiteError(
                f"Agent type '{suite.agent.type}' is not registered; add it to AVAILABLE_AGENTS."
            ) from e

    @staticmethod
    def _existing_agent_type(agent_id: int) -> str:
        agent_type = Agent.objects.filter(pk=agent_id).values_list("agent_type", flat=True).first()
        if agent_type is None:
            raise EvalSuiteError(f"There is no agent with id {agent_id}.")
        return agent_type

    @staticmethod
    def _check_models(loaded: LoadedSuite) -> None:
        user_model = user_model_in_use(loaded)
        targets = [*loaded.suite.models, *judge_models_used_by_metrics(loaded), *([user_model] if user_model else [])]
        if not targets:
            return
        try:
            registered = [provider.NAME for provider in LanguageModelRegistry().get_provider_classes()]
        except (ImportError, ValueError) as e:
            raise EvalSuiteError(
                f"A provider in CATALOG_LANGUAGE_MODEL_PROVIDERS can't be loaded: {str(e).rstrip('.')}. "
                "Check that its plugin is installed and the class path is right."
            ) from e
        for target in targets:
            if target.provider not in registered:
                raise EvalSuiteError(
                    f"Language model provider '{target.provider}' is not installed. Installed: "
                    f"{', '.join(registered) or 'none'}. Install its model plugin and add it to "
                    "CATALOG_LANGUAGE_MODEL_PROVIDERS."
                )

    @staticmethod
    def _check_prompt_files(loaded: LoadedSuite) -> None:
        for variant in loaded.suite.variants:
            if variant.system_prompt_file and not (loaded.base_dir / variant.system_prompt_file).is_file():
                raise EvalSuiteError(f"Variant '{variant.name}': no prompt file {variant.system_prompt_file}.")

    @staticmethod
    def _check_metrics(loaded: LoadedSuite, kind: SuiteKind) -> None:
        registry = MetricRegistry()
        first_seen: dict[str, tuple[str, str | None]] = {}
        for config in loaded.suite.metrics:
            try:
                first_seen[config.name] = (registry.metric_class(config.type).VALUE_TYPE, config.aggregate)
            except MetricError:
                continue
        for case in loaded.cases:
            for config in loaded.suite.metrics_for(case):
                SuiteLoader._check_metric_name(config.name, kind)
                try:
                    metric = registry.build_metric(config, loaded.base_dir)
                except MetricError as e:
                    raise EvalSuiteError(f"Case '{case.id}': {e}") from e
                if not metric.supports(kind):
                    raise EvalSuiteError(f"Metric '{config.name}' ({config.type}) can't measure {kind} suites.")
                params = metric.params
                if isinstance(params, JudgePromptParams) and params.judge is None and loaded.suite.judge is None:
                    raise EvalSuiteError(
                        f"Metric '{config.name}' needs a judge model; set 'judge' in the suite or in its params."
                    )
                SuiteLoader._check_aggregate(config.name, config.aggregate, metric.VALUE_TYPE)
                shape = (metric.VALUE_TYPE, config.aggregate)
                if first_seen.setdefault(config.name, shape) != shape:
                    raise EvalSuiteError(
                        f"Case '{case.id}': metric '{config.name}' must keep the value type and aggregate it has "
                        "elsewhere in the suite, as its results are aggregated together."
                    )

    @staticmethod
    def _check_metric_name(name: str, kind: SuiteKind) -> None:
        if name in reserved_metric_names(kind):
            raise EvalSuiteError(f"Metric name '{name}' is reserved for a built-in figure; pick another.")
        if "." in name:
            raise EvalSuiteError(f"Metric name '{name}' may not contain '.'; reports use it for components.")

    @staticmethod
    def _check_aggregate(name: str, aggregate: str | None, value_type: str) -> None:
        if aggregate == "distribution" and value_type != "label":
            raise EvalSuiteError(f"Metric '{name}': aggregate 'distribution' is only for label metrics.")
        if value_type == "label" and aggregate not in (None, "distribution"):
            raise EvalSuiteError(f"Metric '{name}' is a label metric; its only aggregate is distribution.")

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
            if not isinstance(case, AgenticExecutionEvalCase):
                raise EvalSuiteError(
                    f"Case '{case.id}': 'user_messages' and 'simulated_user' are for conversation suites; set "
                    "'kind: conversation'."
                )
            try:
                execution.INPUT_TYPE(**case.input)
            except ValidationError as e:
                raise EvalSuiteError(f"Case '{case.id}': invalid input: {e}") from e

    @staticmethod
    def _check_conversation_cases(loaded: LoadedSuite, agent_type: str) -> None:
        suite = loaded.suite
        for case in loaded.cases:
            if not isinstance(case, ConversationEvalCase):
                raise EvalSuiteError(
                    f"Case '{case.id}' is an execution case, but this is a conversation suite (agent type "
                    f"'{agent_type}' has no registered execution, or the suite sets 'kind: conversation'); give it "
                    "'user_messages' or 'simulated_user'."
                )
            user = case.simulated_user
            if user is None:
                continue
            if user.class_path is None and suite.user_model is None:
                raise EvalSuiteError(
                    f"Case '{case.id}': a simulated user needs a model; set 'user_model' in the suite."
                )
            if user.goal and suite.judge is None:
                raise EvalSuiteError(
                    f"Case '{case.id}': the judge decides whether the simulated user's goal was reached; set 'judge' "
                    "in the suite."
                )
            if user.class_path is not None:
                try:
                    UserSimulatorRegistry.simulator_class(user.class_path)
                except EvalSuiteError as e:
                    raise EvalSuiteError(f"Case '{case.id}': can't load the user simulator: {e}") from e
