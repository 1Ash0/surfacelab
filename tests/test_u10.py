"""U10 tests: surface loader and apply_variant."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from surfacelab.schema import Surface
from surfacelab.snapshot import surface_hash
from surfacelab.surface import (
    SurfaceLoadError,
    apply_variant,
    load_fixture_surface,
    load_snapshot_surface,
)

# ---------------------------------------------------------------------------
# Fixture surface loader
# ---------------------------------------------------------------------------


class TestLoadFixtureSurface:
    def test_loads_goodserver(self) -> None:
        s = load_fixture_surface("goodserver")
        assert s.server_name == "goodserver"
        assert s.tool_count == 5
        assert s.tools[0].name == "get_weather"

    def test_loads_siblings(self) -> None:
        s = load_fixture_surface("siblings")
        assert s.tool_count == 4

    def test_missing_raises_surface_load_error(self, tmp_path: Path) -> None:
        with pytest.raises(SurfaceLoadError, match="not found"):
            load_fixture_surface("nonexistent", fixtures_dir=tmp_path)

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(SurfaceLoadError):
            load_fixture_surface("bad", fixtures_dir=tmp_path)

    def test_wrong_schema_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"server_name": "x"}', encoding="utf-8")  # missing tools
        with pytest.raises(SurfaceLoadError):
            load_fixture_surface("bad", fixtures_dir=tmp_path)

    def test_surface_id_is_content_addressed(self) -> None:
        """Two loads of the same fixture must have the same surface_hash."""
        s1 = load_fixture_surface("goodserver")
        s2 = load_fixture_surface("goodserver")
        assert surface_hash(s1) == surface_hash(s2)

    def test_different_fixtures_different_hash(self) -> None:
        gs = load_fixture_surface("goodserver")
        sib = load_fixture_surface("siblings")
        assert surface_hash(gs) != surface_hash(sib)


# ---------------------------------------------------------------------------
# Snapshot surface loader
# ---------------------------------------------------------------------------


class TestLoadSnapshotSurface:
    def _make_snapshot_file(self, tmp_path: Path, server_name: str, tools: list[dict]) -> Path:
        snap = {
            "server_name": server_name,
            "surface_hash": "abc123",
            "captured_at": "2026-01-01T00:00:00+00:00",
            "surface": {
                "server_name": server_name,
                "tools": tools,
            },
        }
        p = tmp_path / "snap.json"
        p.write_text(json.dumps(snap), encoding="utf-8")
        return p

    def test_loads_surface_from_snapshot(self, tmp_path: Path) -> None:
        tools = [{"name": "foo", "description": "Foo tool", "input_schema": {}}]
        path = self._make_snapshot_file(tmp_path, "myserver", tools)
        s = load_snapshot_surface(path)
        assert s.server_name == "myserver"
        assert s.tool_count == 1
        assert s.tools[0].name == "foo"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SurfaceLoadError, match="not found"):
            load_snapshot_surface(tmp_path / "no_such.json")

    def test_bad_json_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{{bad", encoding="utf-8")
        with pytest.raises(SurfaceLoadError):
            load_snapshot_surface(p)


# ---------------------------------------------------------------------------
# apply_variant
# ---------------------------------------------------------------------------


class TestApplyVariant:
    def _gs(self) -> Surface:
        return load_fixture_surface("goodserver")

    def test_permute_returns_new_surface(self) -> None:
        base = self._gs()
        variant = apply_variant(base, "permute", seed=42)
        assert isinstance(variant, Surface)
        assert variant is not base

    def test_permute_does_not_mutate_base(self) -> None:
        base = self._gs()
        original_names = [t.name for t in base.tools]
        apply_variant(base, "permute", seed=42)
        assert [t.name for t in base.tools] == original_names

    def test_permute_different_seeds_different_order(self) -> None:
        base = self._gs()
        v1 = apply_variant(base, "permute", seed=1)
        v2 = apply_variant(base, "permute", seed=2)
        # Very likely different (may occasionally collide for tiny surfaces)
        names1 = [t.name for t in v1.tools]
        names2 = [t.name for t in v2.tools]
        assert names1 != names2 or base.tool_count <= 1

    def test_permute_preserves_tool_count(self) -> None:
        base = self._gs()
        variant = apply_variant(base, "permute", seed=7)
        assert variant.tool_count == base.tool_count

    def test_permute_preserves_tool_set(self) -> None:
        base = self._gs()
        variant = apply_variant(base, "permute", seed=7)
        assert {t.name for t in variant.tools} == {t.name for t in base.tools}

    def test_variant_hash_differs_from_base(self) -> None:
        base = self._gs()
        variant = apply_variant(base, "permute", seed=42)
        # The permuted surface likely has a different hash (different tool order)
        assert surface_hash(variant) != surface_hash(base) or base.tool_count <= 1

    def test_unknown_factor_raises(self) -> None:
        base = self._gs()
        with pytest.raises(ValueError, match="Unknown variant factor"):
            apply_variant(base, "nonexistent_factor")
