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
from concurrent.futures import ThreadPoolExecutor
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


def _run_one(
    case: Case,
    variant: Surface,
    variant_index: int,
    harness: Harness,
) -> tuple[TrialResult, RunError | None]:
    h = _surface_hash(variant)
    try:
        emitted = harness(case, variant)
        result = grade(case, emitted)
        return TrialResult(
            case_id=case.id,
            surface_hash=h,
            variant_index=variant_index,
            emitted=emitted,
            correct=result.verdict == Verdict.correct,
            error=None,
        ), None
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        return TrialResult(
            case_id=case.id,
            surface_hash=h,
            variant_index=variant_index,
            emitted=None,
            correct=False,
            error=msg,
        ), RunError(case_id=case.id, variant_index=variant_index, message=msg)


def run_experiment(
    cases: list[Case],
    surface_variants: list[Surface],
    harness: Harness,
    *,
    workers: int = 1,
) -> tuple[list[TrialResult], list[RunError]]:
    """Drive every (case, variant) pair through the harness.

    workers > 1 uses a ThreadPoolExecutor; results are returned in the same
    order as the sequential loop (cases × variants). The harness must be
    thread-safe (CassetteStore.call is; live OpenAI clients are stateless).

    Returns (trials, errors).
    - trials contains one entry per (case, variant) pair, including errored ones.
    - errors is a parallel log of every raised exception.
    """
    work = [
        (case, variant, i)
        for case in cases
        for i, variant in enumerate(surface_variants)
    ]

    if workers <= 1:
        results = [_run_one(c, v, i, harness) for c, v, i in work]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_run_one, c, v, i, harness) for c, v, i in work]
            results = [f.result() for f in futures]

    trials: list[TrialResult] = []
    errors: list[RunError] = []
    for trial, error in results:
        trials.append(trial)
        if error is not None:
            errors.append(error)
    return trials, errors
