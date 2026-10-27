"""U8 tests: runner.run_experiment and report.make_report.

Harnesses are plain callables — no API calls. All expected values computed
before writing assertions.
"""

from __future__ import annotations

import pytest

from surfacelab.cases import Case, CaseKind
from surfacelab.report import make_report
from surfacelab.runner import run_experiment
from surfacelab.schema import Surface, Tool
from surfacelab.snapshot import surface_hash
from surfacelab.stats import wilson_interval

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _case(id: str, gold: set[str], kind: CaseKind = CaseKind.positive) -> Case:
    return Case(
        id=id,
        kind=kind,
        request=f"request for {id}",
        gold=frozenset(gold),
        surface_name="srv",
    )


def _surface(*tool_names: str) -> Surface:
    return Surface(
        server_name="srv",
        tools=[Tool(name=n, description=f"desc {n}") for n in tool_names],
    )


CASE_A = _case("A", {"get_weather"})
CASE_B = _case("B", {"list_files"})
CASE_C = _case("C", {"send_email"})

V0 = _surface("get_weather", "list_files")
V1 = _surface("list_files", "get_weather")  # swapped


def _correct_harness(case: Case, surface: Surface) -> str | None:
    return next(iter(case.gold))


def _wrong_harness(case: Case, surface: Surface) -> str | None:
    return "__not_a_tool__"


def _b_wrong_on_v1(case: Case, surface: Surface) -> str | None:
    if case.id == "B" and surface.tools[0].name == "list_files":
        return "get_weather"  # wrong for case B
    return next(iter(case.gold))


# ---------------------------------------------------------------------------
# run_experiment — trial structure
# ---------------------------------------------------------------------------


def test_run_produces_n_cases_times_n_variants_trials() -> None:
    trials, errors = run_experiment([CASE_A, CASE_B], [V0, V1], _correct_harness)
    assert len(trials) == 4
    assert errors == []


def test_run_correct_harness_all_correct() -> None:
    trials, errors = run_experiment([CASE_A, CASE_B], [V0, V1], _correct_harness)
    assert all(t.correct for t in trials)
    assert errors == []


def test_run_wrong_harness_all_wrong() -> None:
    trials, errors = run_experiment([CASE_A, CASE_B], [V0, V1], _wrong_harness)
    assert not any(t.correct for t in trials)
    assert errors == []


def test_run_mixed_harness_correct_count() -> None:
    # A always correct (2), B correct on v0 only (1) → 3/4 correct
    trials, errors = run_experiment([CASE_A, CASE_B], [V0, V1], _b_wrong_on_v1)
    assert sum(t.correct for t in trials) == 3
    assert errors == []


def test_run_outer_loop_is_cases_inner_is_variants() -> None:
    # Expected order: (A,v0), (A,v1), (B,v0), (B,v1)
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _correct_harness)
    assert [t.case_id for t in trials] == ["A", "A", "B", "B"]
    assert [t.variant_index for t in trials] == [0, 1, 0, 1]


def test_run_records_surface_hash() -> None:
    trials, _ = run_experiment([CASE_A], [V0, V1], _correct_harness)
    assert trials[0].surface_hash == surface_hash(V0)
    assert trials[1].surface_hash == surface_hash(V1)


def test_run_surface_hash_differs_for_different_variants() -> None:
    trials, _ = run_experiment([CASE_A], [V0, V1], _correct_harness)
    assert trials[0].surface_hash != trials[1].surface_hash


def test_run_empty_cases_returns_empty() -> None:
    trials, errors = run_experiment([], [V0], _correct_harness)
    assert trials == []
    assert errors == []


def test_run_empty_variants_returns_empty() -> None:
    trials, errors = run_experiment([CASE_A], [], _correct_harness)
    assert trials == []
    assert errors == []


# ---------------------------------------------------------------------------
# run_experiment — error handling
# ---------------------------------------------------------------------------


def test_run_harness_exception_is_recorded_not_dropped() -> None:
    def boom(case: Case, surface: Surface) -> str | None:
        raise RuntimeError("API timeout")

    trials, errors = run_experiment([CASE_A], [V0], boom)
    # Trial is still recorded
    assert len(trials) == 1
    assert trials[0].correct is False
    assert trials[0].error == "API timeout"
    # Error is also in the errors list
    assert len(errors) == 1
    assert errors[0].case_id == "A"
    assert errors[0].variant_index == 0
    assert "timeout" in errors[0].message


def test_run_exception_on_one_trial_does_not_abort_rest() -> None:
    call_count = 0

    def flaky(case: Case, surface: Surface) -> str | None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # fail on the 2nd of 4 trials
            raise RuntimeError("flake")
        return next(iter(case.gold))

    trials, errors = run_experiment([CASE_A, CASE_B], [V0, V1], flaky)
    assert len(trials) == 4       # all four trials recorded
    assert len(errors) == 1       # one error
    assert sum(t.correct for t in trials) == 3


def test_run_error_trial_has_none_emitted() -> None:
    def boom(case: Case, surface: Surface) -> str | None:
        raise ValueError("bad")

    trials, _ = run_experiment([CASE_A], [V0], boom)
    assert trials[0].emitted is None


# ---------------------------------------------------------------------------
# make_report — aggregate accuracy and CI
# ---------------------------------------------------------------------------


def test_report_aggregate_accuracy_all_correct() -> None:
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _correct_harness)
    report = make_report(trials)
    assert report.n_trials == 4
    assert report.n_correct == 4
    assert report.accuracy == pytest.approx(1.0)


def test_report_aggregate_accuracy_mixed() -> None:
    # 3/4 correct (see _b_wrong_on_v1)
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _b_wrong_on_v1)
    report = make_report(trials)
    assert report.n_correct == 3
    assert report.n_trials == 4
    assert report.accuracy == pytest.approx(0.75)


def test_report_ci_matches_wilson_interval() -> None:
    # 3/4 correct → CI should equal wilson_interval(3, 4)
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _b_wrong_on_v1)
    report = make_report(trials)
    lo, hi = wilson_interval(3, 4)
    assert report.ci_lower == pytest.approx(lo)
    assert report.ci_upper == pytest.approx(hi)


def test_report_ci_contains_accuracy() -> None:
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _b_wrong_on_v1)
    report = make_report(trials)
    assert report.ci_lower <= report.accuracy <= report.ci_upper


def test_report_n_cases() -> None:
    trials, _ = run_experiment([CASE_A, CASE_B, CASE_C], [V0], _correct_harness)
    report = make_report(trials)
    assert report.n_cases == 3


# ---------------------------------------------------------------------------
# make_report — per-family summaries
# ---------------------------------------------------------------------------


def test_report_family_count_matches_cases() -> None:
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _correct_harness)
    report = make_report(trials)
    assert len(report.families) == 2


def test_report_family_accuracy_per_case() -> None:
    # A: 2/2=1.0, B: 1/2=0.5
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _b_wrong_on_v1)
    report = make_report(trials)
    by_id = {f.case_id: f for f in report.families}
    assert by_id["A"].accuracy == pytest.approx(1.0)
    assert by_id["B"].accuracy == pytest.approx(0.5)
    assert by_id["A"].n_correct == 2
    assert by_id["B"].n_correct == 1


def test_report_family_order_matches_case_order() -> None:
    trials, _ = run_experiment([CASE_A, CASE_B], [V0, V1], _correct_harness)
    report = make_report(trials)
    assert report.families[0].case_id == "A"
    assert report.families[1].case_id == "B"


def test_report_error_count() -> None:
    def boom_on_a(case: Case, surface: Surface) -> str | None:
        if case.id == "A":
            raise RuntimeError("fail")
        return next(iter(case.gold))

    trials, _ = run_experiment([CASE_A, CASE_B], [V0], boom_on_a)
    report = make_report(trials)
    assert report.n_errors == 1
    a_fam = next(f for f in report.families if f.case_id == "A")
    assert a_fam.n_errors == 1


def test_report_empty_trials() -> None:
    report = make_report([])
    assert report.n_trials == 0
    assert report.n_cases == 0
    assert report.accuracy == pytest.approx(0.0)
    assert report.ci_lower == pytest.approx(0.0)
    assert report.ci_upper == pytest.approx(1.0)
