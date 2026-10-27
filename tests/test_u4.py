"""U4 tests: permute, all_permutations, balanced_permutations, paraphrase_valid.

All values verified by hand before writing assertions.
"""

from itertools import permutations as stdlib_perms

from surfacelab.schema import Surface, Tool
from surfacelab.variants import (
    all_permutations,
    balanced_permutations,
    paraphrase_valid,
    permute,
)


def make_surface(names: list[str]) -> Surface:
    return Surface(
        server_name="test",
        tools=[Tool(name=n, description=f"Tool {n}") for n in names],
    )


# ---------------------------------------------------------------------------
# permute
# ---------------------------------------------------------------------------


def test_permute_returns_same_tools() -> None:
    s = make_surface(["A", "B", "C"])
    p = permute(s, 0)
    assert {t.name for t in p.tools} == {"A", "B", "C"}


def test_permute_same_seed_same_order() -> None:
    s = make_surface(["A", "B", "C"])
    r1 = [t.name for t in permute(s, 7).tools]
    r2 = [t.name for t in permute(s, 7).tools]
    assert r1 == r2


def test_permute_different_seeds_different_order() -> None:
    # With 4+ tools and 20 seeds at least two distinct orderings must emerge.
    s = make_surface(["A", "B", "C", "D"])
    orders = {tuple(t.name for t in permute(s, seed).tools) for seed in range(20)}
    assert len(orders) > 1


def test_permute_is_pure() -> None:
    """Original surface tools list is unchanged after permute."""
    s = make_surface(["A", "B", "C"])
    original = [t.name for t in s.tools]
    permute(s, seed=99)
    assert [t.name for t in s.tools] == original


def test_permute_preserves_server_name() -> None:
    s = make_surface(["A", "B"])
    assert permute(s, 0).server_name == s.server_name


def test_permute_single_tool_unchanged() -> None:
    s = make_surface(["A"])
    assert [t.name for t in permute(s, 0).tools] == ["A"]


# ---------------------------------------------------------------------------
# all_permutations
# ---------------------------------------------------------------------------


def test_all_permutations_count_n3() -> None:
    s = make_surface(["A", "B", "C"])
    assert len(all_permutations(s)) == 6  # 3! = 6


def test_all_permutations_count_n2() -> None:
    s = make_surface(["A", "B"])
    assert len(all_permutations(s)) == 2  # 2! = 2


def test_all_permutations_exact_balance() -> None:
    """Each tool appears exactly (N-1)! = 2 times at each of the 3 positions."""
    s = make_surface(["A", "B", "C"])
    perms = all_permutations(s)
    for pos in range(3):
        names_at_pos = [p.tools[pos].name for p in perms]
        for tool_name in ["A", "B", "C"]:
            assert names_at_pos.count(tool_name) == 2, (
                f"{tool_name} at position {pos}: expected 2, "
                f"got {names_at_pos.count(tool_name)}"
            )


def test_all_permutations_covers_all_orderings() -> None:
    s = make_surface(["A", "B", "C"])
    result_set = {tuple(t.name for t in p.tools) for p in all_permutations(s)}
    expected = set(stdlib_perms(["A", "B", "C"]))
    assert result_set == expected


def test_all_permutations_is_pure() -> None:
    s = make_surface(["A", "B", "C"])
    original = [t.name for t in s.tools]
    all_permutations(s)
    assert [t.name for t in s.tools] == original


def test_all_permutations_empty_surface() -> None:
    s = make_surface([])
    assert all_permutations(s) == [Surface(server_name="test", tools=[])]


# ---------------------------------------------------------------------------
# balanced_permutations
# ---------------------------------------------------------------------------


def test_balanced_permutations_count() -> None:
    s = make_surface(["A", "B", "C"])
    assert len(balanced_permutations(s, k=4)) == 4


def test_balanced_permutations_full_coverage_small_n() -> None:
    """k >= N! with N<=5 must give all N! orderings."""
    s = make_surface(["A", "B", "C"])
    bperms = balanced_permutations(s, k=6, seed=0)
    assert len(bperms) == 6
    result_set = {tuple(t.name for t in p.tools) for p in bperms}
    assert result_set == set(stdlib_perms(["A", "B", "C"]))


def test_balanced_permutations_deterministic() -> None:
    s = make_surface(["A", "B", "C"])
    r1 = [tuple(t.name for t in p.tools) for p in balanced_permutations(s, k=4, seed=1)]
    r2 = [tuple(t.name for t in p.tools) for p in balanced_permutations(s, k=4, seed=1)]
    assert r1 == r2


def test_balanced_permutations_each_permutation_has_all_tools() -> None:
    s = make_surface(["A", "B", "C"])
    for p in balanced_permutations(s, k=5, seed=0):
        assert {t.name for t in p.tools} == {"A", "B", "C"}


def test_balanced_permutations_k_zero_returns_empty() -> None:
    s = make_surface(["A", "B", "C"])
    assert balanced_permutations(s, k=0) == []


def test_balanced_permutations_large_n_cyclic_coverage() -> None:
    """For N>5, the first N permutations are cyclic shifts: tool[0] visits every position."""
    s = make_surface(["A", "B", "C", "D", "E", "F"])  # N=6
    bperms = balanced_permutations(s, k=6, seed=0)
    assert len(bperms) == 6
    # Each cyclic shift moves A to a new position: A must appear at every position 0..5
    a_positions = [next(i for i, t in enumerate(p.tools) if t.name == "A") for p in bperms]
    assert sorted(a_positions) == list(range(6))


# ---------------------------------------------------------------------------
# paraphrase_valid
# ---------------------------------------------------------------------------


def test_paraphrase_valid_good_paraphrase() -> None:
    ok, _ = paraphrase_valid(
        "What is the weather in Paris right now?",
        "What is the current weather in Paris?",
    )
    assert ok


def test_paraphrase_valid_longer_form_passes() -> None:
    ok, _ = paraphrase_valid(
        "What is the weather in Paris?",
        "Could you tell me the current weather conditions in Paris?",
    )
    assert ok


def test_paraphrase_valid_rejects_identical() -> None:
    ok, reason = paraphrase_valid(
        "What is the weather in Paris?",
        "What is the weather in Paris?",
    )
    assert not ok
    assert "identical" in reason


def test_paraphrase_valid_rejects_too_short() -> None:
    ok, reason = paraphrase_valid(
        "What is the weather in Paris right now?",
        "Hi!",
    )
    assert not ok
    assert "short" in reason


def test_paraphrase_valid_rejects_wrong_proper_noun() -> None:
    # AAPL replaces Paris — different entity, must fail
    ok, reason = paraphrase_valid(
        "What is the weather in Paris?",
        "What is the stock price of AAPL at market close?",
    )
    assert not ok
    assert "paris" in reason.lower()


def test_paraphrase_valid_rejects_too_long() -> None:
    original = "Hi"  # 2 chars
    candidate = "x" * 1000  # ratio >> 4.0
    ok, reason = paraphrase_valid(original, candidate)
    assert not ok
    assert "long" in reason


def test_paraphrase_valid_no_entities_accepts_rewording() -> None:
    # Original has no proper nouns — any valid rewording passes the entity check.
    ok, _ = paraphrase_valid(
        "list all available files",
        "show me the files that are available",
    )
    assert ok


def test_paraphrase_valid_preserves_acronym() -> None:
    # SQL must be in the candidate
    ok, reason = paraphrase_valid(
        "Run the SQL query on the database.",
        "Execute a query on the database.",  # SQL missing
    )
    assert not ok
    assert "sql" in reason.lower()
