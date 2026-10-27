"""U5 tests: variants.edit catalogue, apply_edit, verdict rules.

All hand-computed before writing assertions.
"""

import pytest

from surfacelab.schema import Surface, Tool
from surfacelab.variants import (
    EDIT_CATALOGUE,
    Edit,
    _apply_action,
    apply_edit,
)
from surfacelab.verdicts import Verdict, VerdictParams, apply_verdict


def make_surface(tools: list[tuple[str, str]]) -> Surface:
    return Surface(
        server_name="test",
        tools=[Tool(name=n, description=d) for n, d in tools],
    )


# ---------------------------------------------------------------------------
# Edit catalogue and validation
# ---------------------------------------------------------------------------


def test_edit_catalogue_is_nonempty() -> None:
    assert len(EDIT_CATALOGUE) >= 4


def test_edit_rejects_unknown_edit_id() -> None:
    with pytest.raises(ValueError, match="Unknown edit_id"):
        Edit(edit_id="does_not_exist", tool_name="weather")


def test_edit_valid_construction() -> None:
    e = Edit(edit_id="add_usage_clause", tool_name="get_weather", content="you need weather data")
    assert e.edit_id == "add_usage_clause"
    assert e.tool_name == "get_weather"


# ---------------------------------------------------------------------------
# _apply_action — hand-computed outputs
# ---------------------------------------------------------------------------


def test_add_usage_clause_appends() -> None:
    result = _apply_action("add_usage_clause", "Return the weather.", "checking conditions")
    assert result == "Return the weather. Use when: checking conditions."


def test_add_usage_clause_no_double_period() -> None:
    result = _apply_action("add_usage_clause", "Return the weather.", "checking conditions.")
    assert result.endswith("checking conditions.")
    assert ".." not in result


def test_add_negation_clause_appends() -> None:
    result = _apply_action("add_negation_clause", "Return the weather.", "financial data")
    assert "Do not use for: financial data." in result


def test_prepend_summary_prepends() -> None:
    result = _apply_action("prepend_summary", "Returns weather.", "Get current conditions")
    assert result.startswith("Get current conditions.")
    assert "Returns weather." in result


def test_set_description_replaces() -> None:
    result = _apply_action("set_description", "old description", "brand new description")
    assert result == "brand new description"


def test_trim_to_first_sentence_keeps_first_only() -> None:
    result = _apply_action("trim_to_first_sentence", "First sentence. Second sentence.", "")
    assert result == "First sentence."


def test_trim_to_first_sentence_no_punctuation() -> None:
    # No sentence-ending punctuation: return unchanged
    result = _apply_action("trim_to_first_sentence", "just some text", "")
    assert result == "just some text"


# ---------------------------------------------------------------------------
# apply_edit — pure, raises on unknown tool
# ---------------------------------------------------------------------------


def test_apply_edit_modifies_target_tool() -> None:
    s = make_surface([("get_weather", "Returns weather."), ("list_files", "Lists files.")])
    edit = Edit(edit_id="add_usage_clause", tool_name="get_weather", content="you need weather")
    edited = apply_edit(s, edit)
    assert "Use when:" in edited.tools[0].description
    assert edited.tools[1].description == "Lists files."  # unchanged


def test_apply_edit_is_pure() -> None:
    s = make_surface([("get_weather", "Returns weather.")])
    original_desc = s.tools[0].description
    edit = Edit(edit_id="add_usage_clause", tool_name="get_weather", content="needed")
    apply_edit(s, edit)
    assert s.tools[0].description == original_desc


def test_apply_edit_raises_on_missing_tool() -> None:
    s = make_surface([("get_weather", "Returns weather.")])
    edit = Edit(edit_id="add_usage_clause", tool_name="nonexistent", content="x")
    with pytest.raises(ValueError, match="not found"):
        apply_edit(s, edit)


def test_apply_edit_preserves_server_name() -> None:
    s = Surface(server_name="myserver", tools=[Tool(name="A", description="desc")])
    edited = apply_edit(s, Edit(edit_id="set_description", tool_name="A", content="new"))
    assert edited.server_name == "myserver"


def test_apply_edit_preserves_input_schema() -> None:
    schema = {"type": "object", "properties": {"city": {"type": "string"}}}
    s = Surface(
        server_name="s",
        tools=[Tool(name="A", description="old", input_schema=schema)],
    )
    edited = apply_edit(s, Edit(edit_id="set_description", tool_name="A", content="new"))
    assert edited.tools[0].input_schema == schema


def test_apply_edit_does_not_touch_other_tools() -> None:
    s = make_surface([("A", "desc A"), ("B", "desc B"), ("C", "desc C")])
    edit = Edit(edit_id="set_description", tool_name="B", content="new B")
    edited = apply_edit(s, edit)
    assert edited.tools[0].description == "desc A"
    assert edited.tools[1].description == "new B"
    assert edited.tools[2].description == "desc C"


# ---------------------------------------------------------------------------
# Verdict rules — hand-computed ground truth
#
# Default params: margin=0.05, token_threshold=50
# ---------------------------------------------------------------------------


P = VerdictParams(margin=0.05, token_threshold=50)


def test_verdict_helps_when_ci_above_margin() -> None:
    # ci=(0.10, 0.30): ci_lower=0.10 > 0.05 → helps
    assert apply_verdict(0.10, 0.30, token_delta=20, params=P) == Verdict.helps


def test_verdict_helps_regardless_of_token_delta() -> None:
    # ci entirely above margin → helps even if token_delta is high
    assert apply_verdict(0.10, 0.30, token_delta=200, params=P) == Verdict.helps


def test_verdict_regresses_when_ci_below_neg_margin() -> None:
    # ci=(-0.30, -0.10): ci_upper=-0.10 < -0.05 → regresses
    assert apply_verdict(-0.30, -0.10, token_delta=0, params=P) == Verdict.regresses


def test_verdict_costs_when_ambiguous_accuracy_and_high_delta() -> None:
    # ci=(-0.03, 0.08): straddles zero (not established); token_delta=100 > 50 → costs
    assert apply_verdict(-0.03, 0.08, token_delta=100, params=P) == Verdict.costs


def test_verdict_inconclusive_when_ambiguous_accuracy_low_delta() -> None:
    # ci=(-0.03, 0.08): straddles zero; token_delta=20 ≤ 50 → inconclusive
    assert apply_verdict(-0.03, 0.08, token_delta=20, params=P) == Verdict.inconclusive


def test_verdict_inconclusive_when_ci_positive_but_below_margin() -> None:
    # ci=(0.01, 0.04): ci_lower=0.01 < margin=0.05 (not established above threshold)
    # token_delta=20 ≤ 50 → inconclusive
    assert apply_verdict(0.01, 0.04, token_delta=20, params=P) == Verdict.inconclusive


def test_verdict_costs_when_ci_positive_below_margin_and_high_delta() -> None:
    # ci=(0.01, 0.04): improvement below threshold AND token_delta=100 → costs
    assert apply_verdict(0.01, 0.04, token_delta=100, params=P) == Verdict.costs


def test_verdict_helps_just_at_margin_boundary() -> None:
    # ci_lower exactly at margin: 0.05 > 0.05 is False → NOT helps
    assert apply_verdict(0.05, 0.20, token_delta=0, params=P) != Verdict.helps


def test_verdict_regresses_just_at_neg_margin_boundary() -> None:
    # ci_upper exactly at -margin: -0.05 < -0.05 is False → NOT regresses
    assert apply_verdict(-0.20, -0.05, token_delta=0, params=P) != Verdict.regresses


def test_verdict_custom_params() -> None:
    params = VerdictParams(margin=0.10, token_threshold=20)
    # ci=(0.06, 0.20): ci_lower=0.06 < 0.10 → not helps
    # token_delta=30 > 20 → costs
    assert apply_verdict(0.06, 0.20, token_delta=30, params=params) == Verdict.costs
