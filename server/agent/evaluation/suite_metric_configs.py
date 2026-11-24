from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import MetricConfig


def suite_metric_configs(loaded: LoadedSuite) -> dict[str, MetricConfig]:
    configs = [*loaded.suite.metrics, *(c for case in loaded.cases for c in loaded.suite.metrics_for(case))]
    by_name: dict[str, MetricConfig] = {}
    for config in configs:
        by_name.setdefault(config.name, config)
    return by_name
