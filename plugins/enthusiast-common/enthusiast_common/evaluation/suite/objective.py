from .base import EvalModel
from .objective_constraint import ObjectiveConstraint
from .objective_term import ObjectiveTerm


class Objective(EvalModel):
    """How candidates are ranked: constraints first, then the weighted score."""

    score: list[ObjectiveTerm] = []
    constraints: list[ObjectiveConstraint] = []
