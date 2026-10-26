"""U1 tests: Case schema, fixture loader, grader.

All offline — no model calls. Grader is tested two-sided: correct verdicts and
wrong verdicts, for all three case kinds.
"""

from pathlib import Path

import pytest

from surfacelab.cases import Case, CaseKind, load_cases
from surfacelab.grading import Verdict, grade


FIXTURES = Path(__file__).parent.parent / "fixtures" / "demo_cases.jsonl"


# ---------------------------------------------------------------------------
# Case schema
# ---------------------------------------------------------------------------

def test_positive_case_requires_nonempty_gold():
    with pytest.raises(Exception):
        Case(id="x", kind=CaseKind.positive, request="r", gold=frozenset(), surface_name="s")


def test_abstain_case_requires_empty_gold():
    with pytest.raises(Exception):
        Case(id="x", kind=CaseKind.abstain, request="r", gold=frozenset(["a"]), surface_name="s")


def test_gold_is_a_set_not_ordered():
    c = Case(id="x", kind=CaseKind.positive, request="r",
             gold=frozenset(["tool_a", "tool_b"]), surface_name="s")
    assert "tool_a" in c.gold
    assert "tool_b" in c.gold


# ---------------------------------------------------------------------------
# Fixture loader
# ---------------------------------------------------------------------------

def test_fixture_file_loads():
    cases = load_cases(FIXTURES)
    assert len(cases) == 7


def test_fixture_contains_all_three_kinds():
    cases = load_cases(FIXTURES)
    kinds = {c.kind for c in cases}
    assert CaseKind.positive in kinds
    assert CaseKind.sibling in kinds
    assert CaseKind.abstain in kinds


def test_fixture_ids_are_unique():
    cases = load_cases(FIXTURES)
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Grader — two-sided: correct AND wrong for every kind
# ---------------------------------------------------------------------------

def _case(kind: CaseKind, gold: frozenset[str]) -> Case:
    return Case(id="t", kind=kind, request="r", gold=gold, surface_name="s")


def test_positive_correct_when_emitted_in_gold():
    result = grade(_case(CaseKind.positive, frozenset(["tool_a"])), emitted="tool_a")
    assert result.verdict == Verdict.correct
    assert result.in_gold is True


def test_positive_wrong_when_emitted_not_in_gold():
    result = grade(_case(CaseKind.positive, frozenset(["tool_a"])), emitted="tool_b")
    assert result.verdict == Verdict.wrong
    assert result.in_gold is False


def test_positive_wrong_when_abstained():
    result = grade(_case(CaseKind.positive, frozenset(["tool_a"])), emitted=None)
    assert result.verdict == Verdict.wrong


def test_sibling_correct_when_emitted_in_gold():
    result = grade(_case(CaseKind.sibling, frozenset(["right_tool"])), emitted="right_tool")
    assert result.verdict == Verdict.correct


def test_sibling_wrong_when_sibling_chosen():
    result = grade(_case(CaseKind.sibling, frozenset(["right_tool"])), emitted="sibling_tool")
    assert result.verdict == Verdict.wrong


def test_abstain_correct_when_no_tool_called():
    result = grade(_case(CaseKind.abstain, frozenset()), emitted=None)
    assert result.verdict == Verdict.correct


def test_abstain_wrong_when_any_tool_called():
    result = grade(_case(CaseKind.abstain, frozenset()), emitted="any_tool")
    assert result.verdict == Verdict.wrong
    assert result.in_gold is False


def test_gold_set_accepts_either_tool():
    """When gold has two tools, either one is a correct grade."""
    c = _case(CaseKind.positive, frozenset(["tool_a", "tool_b"]))
    assert grade(c, "tool_a").verdict == Verdict.correct
    assert grade(c, "tool_b").verdict == Verdict.correct
    assert grade(c, "tool_c").verdict == Verdict.wrong
