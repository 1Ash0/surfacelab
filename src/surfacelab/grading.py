"""Primary grader: exact tool-name match against the gold set.

Grade is determined by the first tool_name the model emitted (or None for
abstain). No LLM judge, no partial credit. This is intentional (ADR-002):
we measure which tool was chosen, not whether the choice was reasonable.

The four verdicts map cleanly to a 2×2 table:
                    model called a tool    model abstained
case expects a tool      correct               wrong
case expects nothing     wrong                 correct
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .cases import Case, CaseKind


class Verdict(str, Enum):
    correct = "correct"  # emitted tool is in gold set, or abstained when expected
    wrong   = "wrong"    # emitted tool not in gold set, or called when should abstain


@dataclass(frozen=True)
class GradeResult:
    case_id:  str
    emitted:  str | None   # tool name the model called; None = model abstained
    verdict:  Verdict
    in_gold:  bool         # True iff emitted is not None and emitted in case.gold


def grade(case: Case, emitted: str | None) -> GradeResult:
    """Grade one trial.

    Args:
        case:    the case being evaluated
        emitted: the tool name from the model's first tool_use block, or None
                 if the model produced no tool call
    """
    if case.kind == CaseKind.abstain:
        correct = emitted is None
    else:
        correct = emitted is not None and emitted in case.gold

    return GradeResult(
        case_id=case.id,
        emitted=emitted,
        verdict=Verdict.correct if correct else Verdict.wrong,
        in_gold=emitted is not None and emitted in case.gold,
    )
