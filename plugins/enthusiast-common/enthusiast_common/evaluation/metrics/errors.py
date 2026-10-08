class MetricError(Exception):
    """Base for errors raised while setting up or measuring metrics."""


class MetricNotFoundError(MetricError):
    """A metric type is neither a built-in NAME nor an importable BaseMetric subclass."""


class MetricConfigError(MetricError):
    """A metric's params do not fit its PARAMS model."""
