from enthusiast_common.evaluation.suite import EvalSuite, SuiteKind


def resolved_kind(suite: EvalSuite) -> SuiteKind:
    """The suite's kind; one built in code rather than through SuiteLoader may leave it out, and runs as an execution."""
    return suite.kind or SuiteKind.EXECUTION
