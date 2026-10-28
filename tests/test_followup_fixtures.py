"""Consistency checks for EXP-009–012 fixtures (ADR-023). Offline."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from surfacelab.cases import load_cases
from surfacelab.surface import load_fixture_surface

ND = ["nd_files", "nd_messaging", "nd_documents", "nd_calendar"]
XO = ["files", "mail", "knowledge"]
NEAR_DUP = load_cases(Path("fixtures/cases/near_dup.jsonl"))
CROSS = load_cases(Path("fixtures/cases/cross_overlap.jsonl"))


def names(surface: str) -> list[str]:
    return [t.name for t in load_fixture_surface(surface).tools]


def test_case_counts_and_unique_ids() -> None:
    assert len(NEAR_DUP) == 32 and len(CROSS) == 24
    ids = [c.id for c in NEAR_DUP + CROSS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("surface", ND)
def test_two_cases_per_tool_and_gold_exists(surface: str) -> None:
    tools = names(surface)
    assert len(tools) == 4
    cases = [c for c in NEAR_DUP if c.surface_name == surface]
    golds = Counter(g for c in cases for g in c.gold)
    assert golds == {t: 2 for t in tools}


@pytest.mark.parametrize("surface", ND)
@pytest.mark.parametrize("edit", ["contrast", "negation"])
def test_edits_only_append_to_base_descriptions(surface: str, edit: str) -> None:
    base = load_fixture_surface(surface).tools
    edited = load_fixture_surface(f"{surface}_{edit}").tools
    assert [t.name for t in base] == [t.name for t in edited]
    for b, e in zip(base, edited):
        assert e.description.startswith(b.description) and len(e.description) > len(b.description)
        for other in base:  # contrast/negation may only point at tools on the same surface
            if other.name != b.name and edit == "contrast":
                assert f"`{other.name}`" in e.description


@pytest.mark.parametrize("surface", ND)
def test_distractors_are_new_names(surface: str) -> None:
    pool = names(f"distractors/{surface}")
    assert len(pool) == 20 and len(set(pool)) == 20
    assert not set(pool) & set(names(surface))


@pytest.mark.parametrize("pair", XO)
def test_cross_server_schemes_and_gold(pair: str) -> None:
    none, prefix, qualified = (names(f"xo_{pair}_{s}") for s in ["none", "prefix", "qualified"])
    assert len(none) == len(prefix) == len(qualified) == 6
    assert len(set(none)) == 6  # uninformative suffix keeps names unique
    assert all("/" in q for q in qualified)
    assert [q.replace("/", "_") for q in qualified] == prefix
    cases = [c for c in CROSS if c.surface_name == f"xo_{pair}_qualified"]
    assert len(cases) == 8
    servers = Counter(next(iter(c.gold)).split("/")[0] for c in cases)
    assert list(servers.values()) == [4, 4]
    assert all(next(iter(c.gold)) in qualified for c in cases)
