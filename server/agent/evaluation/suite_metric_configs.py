from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import MetricConfig


def suite_metric_configs(loaded: LoadedSuite) -> dict[str, MetricConfig]:
    """Every metric a suite measures, by name, suite-level ones first then those only cases add.

    The first config of a name stands for every case: SuiteLoader makes a case's override keep its value type and
    aggregate, so it describes how the metric's results are aggregated and reported.
    """
    configs = [*loaded.suite.metrics, *(c for case in loaded.cases for c in loaded.suite.metrics_for(case))]
    by_name: dict[str, MetricConfig] = {}
    for config in configs:
        by_name.setdefault(config.name, config)
    return by_name
