from suvereo_common.evaluation.metrics.auto import AUTO_METRICS
from suvereo_common.evaluation.metrics.correctness import CORRECTNESS_METRICS
from suvereo_common.evaluation.metrics.llm import LLM_METRICS
from suvereo_common.evaluation.metrics.process import PROCESS_METRICS

BUILTIN_METRICS = [*AUTO_METRICS, *CORRECTNESS_METRICS, *PROCESS_METRICS, *LLM_METRICS]
