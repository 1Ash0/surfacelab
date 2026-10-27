"""U13 — merge_surfaces and pad_surface variants (EXP-004, EXP-005).

Two-sided tests: one that must fire, one that must not (per CLAUDE.md rule 8).
"""

from __future__ import annotations

import pytest

from surfacelab.schema import Surface, Tool
from surfacelab.variants import merge_surfaces, pad_surface

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _surface(name: str, tools: list[tuple[str, str]]) -> Surface:
    return Surface(
        server_name=name,
        tools=[Tool(name=n, description=d) for n, d in tools],
    )


ALPHA = _surface("alpha", [("get_weather", "weather"), ("search_web", "search")])
BETA = _surface("beta", [("read_file", "file"), ("send_email", "email")])
GAMMA = _surface("gamma", [("get_weather", "also weather")])  # name collision with ALPHA


# ---------------------------------------------------------------------------
# merge_surfaces — namespacing modes
# ---------------------------------------------------------------------------


class TestMergeNone:
    def test_tool_count_is_sum(self) -> None:
        m = merge_surfaces([ALPHA, BETA], "none")
        assert len(m.tools) == 4

    def test_names_unchanged(self) -> None:
        m = merge_surfaces([ALPHA, BETA], "none")
        assert m.tools[0].name == "get_weather"
        assert m.tools[2].name == "read_file"

    def test_collision_preserved(self) -> None:
        # "none" intentionally allows collisions — they are the EXP-004 signal
        m = merge_surfaces([ALPHA, GAMMA], "none")
        names = [t.name for t in m.tools]
        assert names.count("get_weather") == 2

    def test_server_name_is_joined(self) -> None:
        m = merge_surfaces([ALPHA, BETA], "none")
        assert m.server_name == "alpha|beta"

    def test_empty_list_returns_empty(self) -> None:
        m = merge_surfaces([], "none")
        assert m.tools == []

    def test_single_surface_unchanged(self) -> None:
        m = merge_surfaces([ALPHA], "none")
        assert [t.name for t in m.tools] == [t.name for t in ALPHA.tools]


class TestMergePrefix:
    def test_names_prefixed(self) -> None:
        m = merge_surfaces([ALPHA, BETA], "prefix")
        assert m.tools[0].name == "alpha_get_weather"
        assert m.tools[2].name == "beta_read_file"

    def test_collision_resolved(self) -> None:
        m = merge_surfaces([ALPHA, GAMMA], "prefix")
        names = [t.name for t in m.tools]
        assert "alpha_get_weather" in names
        assert "gamma_get_weather" in names
        assert names.count("get_weather") == 0

    def test_descriptions_unchanged(self) -> None:
        m = merge_surfaces([ALPHA], "prefix")
        assert m.tools[0].description == "weather"


class TestMergeQualified:
    def test_names_qualified(self) -> None:
        m = merge_surfaces([ALPHA, BETA], "qualified")
        assert m.tools[0].name == "alpha/get_weather"
        assert m.tools[3].name == "beta/send_email"

    def test_slash_separator(self) -> None:
        m = merge_surfaces([ALPHA], "qualified")
        assert "/" in m.tools[0].name
        assert "_" not in m.tools[0].name.split("/")[0]


class TestMergeErrors:
    def test_unknown_namespacing_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown namespacing"):
            merge_surfaces([ALPHA], "invalid")

    def test_pure_does_not_mutate(self) -> None:
        original_names = [t.name for t in ALPHA.tools]
        merge_surfaces([ALPHA, BETA], "prefix")
        assert [t.name for t in ALPHA.tools] == original_names


# ---------------------------------------------------------------------------
# pad_surface — distractor kinds
# ---------------------------------------------------------------------------


class TestPadUnrelated:
    def test_count_added(self) -> None:
        p = pad_surface(ALPHA, 5, "unrelated")
        assert len(p.tools) == len(ALPHA.tools) + 5

    def test_original_tools_first(self) -> None:
        p = pad_surface(ALPHA, 3, "unrelated")
        assert p.tools[0].name == "get_weather"
        assert p.tools[1].name == "search_web"

    def test_distractor_names_unique(self) -> None:
        p = pad_surface(ALPHA, 10, "unrelated")
        names = [t.name for t in p.tools[2:]]
        assert len(set(names)) == len(names)

    def test_zero_pad_unchanged(self) -> None:
        p = pad_surface(ALPHA, 0, "unrelated")
        assert len(p.tools) == len(ALPHA.tools)

    def test_pure_does_not_mutate(self) -> None:
        original_count = len(ALPHA.tools)
        pad_surface(ALPHA, 5, "unrelated")
        assert len(ALPHA.tools) == original_count


class TestPadSameDomain:
    def test_count_added(self) -> None:
        p = pad_surface(ALPHA, 4, "same-domain")
        assert len(p.tools) == len(ALPHA.tools) + 4

    def test_descriptions_nonempty(self) -> None:
        p = pad_surface(ALPHA, 3, "same-domain")
        for tool in p.tools[2:]:
            assert len(tool.description) > 10


class TestPadNearDuplicate:
    def test_count_added(self) -> None:
        p = pad_surface(ALPHA, 6, "near-duplicate")
        assert len(p.tools) == len(ALPHA.tools) + 6

    def test_distractors_resemble_domain(self) -> None:
        p = pad_surface(ALPHA, 3, "near-duplicate")
        # near-duplicates should mention weather/search/file/email/calendar
        keywords = {"weather", "search", "file", "email", "calendar", "web"}
        for tool in p.tools[2:]:
            assert any(kw in tool.description.lower() for kw in keywords), tool.description


class TestPadLargeN:
    def test_cycles_pool_when_n_exceeds_pool(self) -> None:
        # Pool has 20 unrelated entries; request 25 — should cycle without error
        p = pad_surface(ALPHA, 25, "unrelated")
        assert len(p.tools) == len(ALPHA.tools) + 25

    def test_seed_deterministic(self) -> None:
        p1 = pad_surface(ALPHA, 5, "unrelated", seed=7)
        p2 = pad_surface(ALPHA, 5, "unrelated", seed=7)
        assert [t.name for t in p1.tools] == [t.name for t in p2.tools]

    def test_different_seeds_differ(self) -> None:
        p1 = pad_surface(ALPHA, 5, "unrelated", seed=1)
        p2 = pad_surface(ALPHA, 5, "unrelated", seed=2)
        assert [t.name for t in p1.tools[2:]] != [t.name for t in p2.tools[2:]]


class TestPadErrors:
    def test_unknown_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown pad kind"):
            pad_surface(ALPHA, 3, "bogus")

    def test_negative_n_raises(self) -> None:
        with pytest.raises(ValueError, match="n must be"):
            pad_surface(ALPHA, -1, "unrelated")
