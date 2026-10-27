"""Experiment runner: drive (case, surface_variant) pairs through a harness.

The Harness is a plain callable — the only place live API calls may cross.
In tests, pass a fake harness that returns scripted answers. In production,
pass a function that calls the Anthropic API (guarded by budget.check first).

Harness exceptions are *never* silently treated as incorrect answers:
- Each failed trial gets correct=False AND error set to the exception message.
- The caller inspects RunErrors and decides whether to abort or proceed.

Trial layout: outer loop = cases, inner loop = variants. All K variant trials
of one case form a *family* — the unit of clustered statistics in report.py.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cases import Case
from .grading import Verdict, grade
from .schema import Surface
from .snapshot import surface_hash as _surface_hash

Harness = Callable[[Case, Surface], "str | None"]
"""A function that returns the tool name emitted by a model (or None for
abstain). May call the Anthropic API, replay a cassette, or return a
scripted value. Raised exceptions are caught and recorded as RunErrors."""


@dataclass(frozen=True)
class TrialResult:
    """One (case, surface_variant) trial outcome."""

    case_id: str
    surface_hash: str      # sha256 of the variant surface bytes
    variant_index: int     # 0-based index into the surface_variants list
    emitted: str | None    # tool name the harness returned; None = abstain
    correct: bool          # True iff grade(case, emitted).verdict == correct
    error: str | None      # set when harness raised; correct is False


@dataclass(frozen=True)
class RunError:
    """Records a harness exception without aborting the rest of the run."""

    case_id: str
    variant_index: int
    message: str


def run_experiment(
    cases: list[Case],
    surface_variants: list[Surface],
    harness: Harness,
) -> tuple[list[TrialResult], list[RunError]]:
    """Drive every (case, variant) pair through the harness.

    Returns (trials, errors).
    - trials contains one entry per (case, variant) pair, including errored ones.
    - errors is a parallel log of every raised exception.

    Errors are NOT silently dropped: each error trial has correct=False and
    error set to the exception message. The caller inspects errors to decide
    whether the run is valid.
    """
    trials: list[TrialResult] = []
    errors: list[RunError] = []

    for case in cases:
        for i, variant in enumerate(surface_variants):
            h = _surface_hash(variant)
            try:
                emitted = harness(case, variant)
                result = grade(case, emitted)
                trials.append(TrialResult(
                    case_id=case.id,
                    surface_hash=h,
                    variant_index=i,
                    emitted=emitted,
                    correct=result.verdict == Verdict.correct,
                    error=None,
                ))
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                errors.append(RunError(case_id=case.id, variant_index=i, message=msg))
                trials.append(TrialResult(
                    case_id=case.id,
                    surface_hash=h,
                    variant_index=i,
                    emitted=None,
                    correct=False,
                    error=msg,
                ))

    return trials, errors
