"""U7 tests: Snapshot, SnapshotStore, drift classifier.

Hash sensitivity: order, server_name, description all change the hash.
Store: idempotent save, load, load_latest, exists.
Drift: all five DriftKinds including mixed transitions.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from surfacelab.schema import Surface, Tool
from surfacelab.snapshot import (
    DriftKind,
    Snapshot,
    SnapshotStore,
    classify_drift,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_surface(server: str, tools: list[tuple[str, str]]) -> Surface:
    return Surface(
        server_name=server,
        tools=[Tool(name=n, description=d) for n, d in tools],
    )


TS = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Snapshot.capture — content hash properties
# ---------------------------------------------------------------------------


def test_snapshot_hash_is_deterministic() -> None:
    s = make_surface("srv", [("A", "foo"), ("B", "bar")])
    h1 = Snapshot.capture(s, captured_at=TS).surface_hash
    h2 = Snapshot.capture(s, captured_at=TS).surface_hash
    assert h1 == h2


def test_snapshot_hash_changes_with_tool_order() -> None:
    s1 = make_surface("srv", [("A", "foo"), ("B", "bar")])
    s2 = make_surface("srv", [("B", "bar"), ("A", "foo")])
    assert Snapshot.capture(s1, TS).surface_hash != Snapshot.capture(s2, TS).surface_hash


def test_snapshot_hash_changes_with_server_name() -> None:
    s1 = make_surface("dev", [("A", "foo")])
    s2 = make_surface("prod", [("A", "foo")])
    assert Snapshot.capture(s1, TS).surface_hash != Snapshot.capture(s2, TS).surface_hash


def test_snapshot_hash_changes_with_description() -> None:
    s1 = make_surface("srv", [("A", "Returns weather.")])
    s2 = make_surface("srv", [("A", "Returns current weather.")])
    assert Snapshot.capture(s1, TS).surface_hash != Snapshot.capture(s2, TS).surface_hash


def test_snapshot_hash_is_hex_string() -> None:
    s = make_surface("srv", [("A", "foo")])
    h = Snapshot.capture(s, TS).surface_hash
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_snapshot_roundtrip() -> None:
    s = make_surface("srv", [("A", "foo"), ("B", "bar")])
    snap = Snapshot.capture(s, captured_at=TS)
    restored = Snapshot.from_dict(snap.to_dict())
    assert restored.server_name == snap.server_name
    assert restored.surface_hash == snap.surface_hash
    assert restored.captured_at == snap.captured_at
    assert [t.name for t in restored.surface.tools] == ["A", "B"]


def test_snapshot_captures_utc_when_no_timestamp() -> None:
    s = make_surface("srv", [("A", "foo")])
    snap = Snapshot.capture(s)
    assert snap.captured_at.tzinfo is not None


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------


def test_store_save_and_load(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    snap = Snapshot.capture(make_surface("srv", [("A", "foo")]), TS)
    store.save(snap)
    loaded = store.load("srv", snap.surface_hash)
    assert loaded.surface_hash == snap.surface_hash
    assert loaded.server_name == "srv"


def test_store_save_is_idempotent(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    snap = Snapshot.capture(make_surface("srv", [("A", "foo")]), TS)
    path1 = store.save(snap)
    mtime1 = path1.stat().st_mtime
    path2 = store.save(snap)
    assert path1 == path2
    # File is NOT rewritten — mtime unchanged.
    assert path1.stat().st_mtime == mtime1


def test_store_load_latest_returns_most_recent(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    snap1 = Snapshot.capture(make_surface("srv", [("A", "v1")]), TS)
    snap2 = Snapshot.capture(make_surface("srv", [("A", "v2")]), TS)
    store.save(snap1)
    store.save(snap2)
    latest = store.load_latest("srv")
    assert latest.surface_hash == snap2.surface_hash


def test_store_load_missing_raises_key_error(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    with pytest.raises(KeyError):
        store.load("srv", "a" * 64)


def test_store_load_latest_missing_raises_key_error(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    with pytest.raises(KeyError):
        store.load_latest("no_such_server")


def test_store_exists(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    snap = Snapshot.capture(make_surface("srv", [("A", "foo")]), TS)
    assert not store.exists("srv", snap.surface_hash)
    store.save(snap)
    assert store.exists("srv", snap.surface_hash)


def test_store_creates_server_directory(tmp_path: Path) -> None:
    store = SnapshotStore(tmp_path)
    snap = Snapshot.capture(make_surface("new_server", [("A", "foo")]), TS)
    store.save(snap)
    assert (tmp_path / "new_server").is_dir()


# ---------------------------------------------------------------------------
# classify_drift
# ---------------------------------------------------------------------------


def _snap(server: str, tools: list[tuple[str, str]]) -> Snapshot:
    return Snapshot.capture(make_surface(server, tools), captured_at=TS)


def test_drift_unchanged_when_hashes_equal() -> None:
    snap = _snap("srv", [("A", "foo"), ("B", "bar")])
    events = classify_drift(snap, snap)
    assert len(events) == 1
    assert events[0].kind == DriftKind.unchanged


def test_drift_added_tool() -> None:
    old = _snap("srv", [("A", "foo")])
    new = _snap("srv", [("A", "foo"), ("B", "bar")])
    events = classify_drift(old, new)
    kinds = {e.kind for e in events}
    names = {e.tool_name for e in events if e.tool_name}
    assert DriftKind.added in kinds
    assert "B" in names


def test_drift_removed_tool() -> None:
    old = _snap("srv", [("A", "foo"), ("B", "bar")])
    new = _snap("srv", [("A", "foo")])
    events = classify_drift(old, new)
    kinds = {e.kind for e in events}
    names = {e.tool_name for e in events if e.tool_name}
    assert DriftKind.removed in kinds
    assert "B" in names


def test_drift_description_changed() -> None:
    old = _snap("srv", [("A", "Returns weather.")])
    new = _snap("srv", [("A", "Returns current weather.")])
    events = classify_drift(old, new)
    assert len(events) == 1
    e = events[0]
    assert e.kind == DriftKind.description_changed
    assert e.tool_name == "A"
    assert e.old_description == "Returns weather."
    assert e.new_description == "Returns current weather."


def test_drift_reordered() -> None:
    old = _snap("srv", [("A", "foo"), ("B", "bar")])
    new = _snap("srv", [("B", "bar"), ("A", "foo")])
    events = classify_drift(old, new)
    assert len(events) == 1
    assert events[0].kind == DriftKind.reordered


def test_drift_rename_is_reported_as_remove_and_add() -> None:
    # [A, B, C] → [A, C, D]: B removed, D added; no rename inference
    old = _snap("srv", [("A", "foo"), ("B", "bar"), ("C", "baz")])
    new = _snap("srv", [("A", "foo"), ("C", "baz"), ("D", "qux")])
    events = classify_drift(old, new)
    kinds = {e.kind for e in events}
    assert DriftKind.removed in kinds
    assert DriftKind.added in kinds
    removed_names = {e.tool_name for e in events if e.kind == DriftKind.removed}
    added_names = {e.tool_name for e in events if e.kind == DriftKind.added}
    assert removed_names == {"B"}
    assert added_names == {"D"}


def test_drift_mixed_add_and_description_change() -> None:
    old = _snap("srv", [("A", "foo"), ("B", "bar")])
    new = _snap("srv", [("A", "new foo"), ("B", "bar"), ("C", "baz")])
    events = classify_drift(old, new)
    kinds = {e.kind for e in events}
    assert DriftKind.added in kinds
    assert DriftKind.description_changed in kinds
    assert DriftKind.removed not in kinds


def test_drift_no_reorder_when_only_add() -> None:
    # Adding a tool at the end should not trigger reorder for existing tools
    old = _snap("srv", [("A", "foo"), ("B", "bar")])
    new = _snap("srv", [("A", "foo"), ("B", "bar"), ("C", "baz")])
    events = classify_drift(old, new)
    kinds = {e.kind for e in events}
    assert DriftKind.reordered not in kinds
    assert DriftKind.added in kinds


def test_drift_no_unchanged_when_changes_present() -> None:
    old = _snap("srv", [("A", "foo")])
    new = _snap("srv", [("A", "bar")])
    events = classify_drift(old, new)
    kinds = {e.kind for e in events}
    assert DriftKind.unchanged not in kinds
