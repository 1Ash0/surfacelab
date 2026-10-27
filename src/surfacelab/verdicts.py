"""Verdict rules for description-edit experiments (EXP-003).

A verdict maps (accuracy CI, token delta) to one of four outcomes. The rule
is fixed in the preregistration BEFORE any data is collected; changing it
after seeing results is the definition of p-hacking.

Outcome semantics
-----------------
helps      — CI entirely above +margin: accuracy improvement is established
             and exceeds the minimum practically-significant threshold.
regresses  — CI entirely below −margin: the edit reliably hurts.
costs      — accuracy is ambiguous (CI not established positive or negative)
             AND the edit adds more than token_threshold tokens. The edit
             consumes resources without demonstrated benefit.
inconclusive — accuracy ambiguous, token cost acceptable. The experiment
             cannot distinguish the edit's effect from noise at this n.

`inconclusive` is not a failure — it is an honest answer. Report it as such.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    helps = "helps"
    regresses = "regresses"
    costs = "costs"
    inconclusive = "inconclusive"


@dataclass(frozen=True)
class VerdictParams:
    """Parameters fixed at preregistration. Change only with a new experiment id.

    margin:          minimum accuracy delta (percentage points as a fraction)
                     for the verdict to be 'helps' or 'regresses'. Default 0.05
                     means a 5 pp improvement must be established.
    token_threshold: extra tokens beyond which 'costs' applies when accuracy
                     is ambiguous. Default 50 tokens (~38 words).
    alpha:           family-wise significance level for Holm correction across
                     all confirmatory edit tests in the experiment.
    """

    margin: float = 0.05
    token_threshold: int = 50
    alpha: float = 0.05


def apply_verdict(
    ci_lower: float,
    ci_upper: float,
    token_delta: int,
    params: VerdictParams | None = None,
) -> Verdict:
    """Map (accuracy delta CI, token delta) to a Verdict.

    ci_lower / ci_upper: bounds of the confidence interval on the accuracy
    delta (edited − baseline), e.g. from clustered_bootstrap or McNemar.
    token_delta: tokens(edited description) − tokens(original description).
    A negative delta means the edit shortened the description.

    params defaults to VerdictParams() when None.

    Decision tree (evaluated in order):
    1. ci_lower > margin        → helps   (CI entirely above minimum threshold)
    2. ci_upper < −margin       → regresses
    3. token_delta > threshold  → costs   (ambiguous accuracy, high token cost)
    4. otherwise                → inconclusive
    """
    if params is None:
        params = VerdictParams()
    if ci_lower > params.margin:
        return Verdict.helps
    if ci_upper < -params.margin:
        return Verdict.regresses
    if token_delta > params.token_threshold:
        return Verdict.costs
    return Verdict.inconclusive
