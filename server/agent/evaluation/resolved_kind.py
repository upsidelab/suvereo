from suvereo_common.evaluation.suite import EvalSuite, SuiteKind


def resolved_kind(suite: EvalSuite) -> SuiteKind:
    return suite.kind or SuiteKind.EXECUTION
