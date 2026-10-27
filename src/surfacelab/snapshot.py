"""Snapshot: content-addressed record of a surface at a point in time.

A Snapshot captures the full tool list returned by tools/list, a timestamp,
and a sha256 of the surface bytes. The hash is the stable identity — two
snapshots with the same hash have identical surfaces (same tools, same
descriptions, same order).

The SnapshotStore persists snapshots to disk under
runs/snapshots/<server_name>/<hash>.json. Save is idempotent: an existing
file with the correct hash is never overwritten.

The drift classifier compares two snapshots and returns a list of DriftEvents
describing what changed: tools added, removed, descriptions changed, or order
changed among the common tools.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .schema import Surface, Tool

# ---------------------------------------------------------------------------
# Deterministic serialization (for hashing only — not the API render format)
# ---------------------------------------------------------------------------

def _surface_bytes(surface: Surface) -> bytes:
    """Stable bytes representation of a surface. Order is preserved."""
    data = {
        "server_name": surface.server_name,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in surface.tools
        ],
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def _hash_surface(surface: Surface) -> str:
    return hashlib.sha256(_surface_bytes(surface)).hexdigest()


def surface_hash(surface: Surface) -> str:
    """Public alias: sha256 hex digest of a surface's canonical bytes."""
    return _hash_surface(surface)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Snapshot:
    """Immutable, content-addressed record of a surface at one point in time."""

    server_name: str
    surface: Surface
    captured_at: datetime
    surface_hash: str  # sha256 hex of _surface_bytes(surface)

    @classmethod
    def capture(
        cls,
        surface: Surface,
        captured_at: datetime | None = None,
    ) -> Snapshot:
        """Create a Snapshot from a live Surface. Timestamps in UTC."""
        if captured_at is None:
            captured_at = datetime.now(tz=UTC)
        return cls(
            server_name=surface.server_name,
            surface=surface,
            captured_at=captured_at,
            surface_hash=_hash_surface(surface),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_name": self.server_name,
            "captured_at": self.captured_at.isoformat(),
            "surface_hash": self.surface_hash,
            "tools": [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in self.surface.tools
            ],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Snapshot:
        tools = [
            Tool.model_validate({"name": t["name"], "description": t["description"],
                                 "inputSchema": t.get("input_schema") or {}})
            for t in d["tools"]
        ]
        surface = Surface(server_name=d["server_name"], tools=tools)
        return cls(
            server_name=d["server_name"],
            surface=surface,
            captured_at=datetime.fromisoformat(d["captured_at"]),
            surface_hash=d["surface_hash"],
        )


# ---------------------------------------------------------------------------
# Snapshot store
# ---------------------------------------------------------------------------

class SnapshotStore:
    """Persist and retrieve snapshots under root/<server_name>/<hash>.json.

    Save is idempotent: if a file with the correct hash already exists it is
    not rewritten. The latest pointer (latest.txt) is always updated.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, snapshot: Snapshot) -> Path:
        """Write snapshot to disk. Returns the path written (or already existing)."""
        server_dir = self.root / snapshot.server_name
        server_dir.mkdir(parents=True, exist_ok=True)

        path = server_dir / f"{snapshot.surface_hash}.json"
        if not path.exists():
            path.write_text(
                json.dumps(snapshot.to_dict(), indent=2),
                encoding="utf-8",
            )

        # Update latest pointer regardless of whether we wrote a new file.
        (server_dir / "latest.txt").write_text(snapshot.surface_hash, encoding="utf-8")
        return path

    def load(self, server_name: str, surface_hash: str) -> Snapshot:
        """Load a specific snapshot by hash. Raises KeyError if not found."""
        path = self.root / server_name / f"{surface_hash}.json"
        if not path.exists():
            raise KeyError(f"Snapshot not found: {server_name}/{surface_hash}")
        return Snapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def load_latest(self, server_name: str) -> Snapshot:
        """Load the most recently saved snapshot for a server."""
        latest = self.root / server_name / "latest.txt"
        if not latest.exists():
            raise KeyError(f"No snapshots for server: {server_name!r}")
        surface_hash = latest.read_text(encoding="utf-8").strip()
        return self.load(server_name, surface_hash)

    def exists(self, server_name: str, surface_hash: str) -> bool:
        return (self.root / server_name / f"{surface_hash}.json").exists()


# ---------------------------------------------------------------------------
# Drift classifier
# ---------------------------------------------------------------------------

class DriftKind(str, Enum):
    unchanged = "unchanged"
    added = "added"
    removed = "removed"
    description_changed = "description_changed"
    reordered = "reordered"


@dataclass(frozen=True)
class DriftEvent:
    kind: DriftKind
    tool_name: str | None = None
    old_description: str | None = None
    new_description: str | None = None


def classify_drift(old: Snapshot, new: Snapshot) -> list[DriftEvent]:
    """Return a list of DriftEvents describing what changed between snapshots.

    Returns [DriftEvent(kind=unchanged)] when the hashes are equal.
    A rename is indistinguishable from remove+add without a stable tool id;
    the classifier reports removed and added separately.
    """
    if old.surface_hash == new.surface_hash:
        return [DriftEvent(kind=DriftKind.unchanged)]

    old_map = {t.name: t for t in old.surface.tools}
    new_map = {t.name: t for t in new.surface.tools}

    events: list[DriftEvent] = []

    for name in new_map:
        if name not in old_map:
            events.append(DriftEvent(kind=DriftKind.added, tool_name=name))

    for name in old_map:
        if name not in new_map:
            events.append(DriftEvent(kind=DriftKind.removed, tool_name=name))

    for name, old_tool in old_map.items():
        if name in new_map and old_tool.description != new_map[name].description:
            events.append(DriftEvent(
                kind=DriftKind.description_changed,
                tool_name=name,
                old_description=old_tool.description,
                new_description=new_map[name].description,
            ))

    # Reordering: relative order of the tools common to both snapshots changed.
    common_old = [t.name for t in old.surface.tools if t.name in new_map]
    common_new = [t.name for t in new.surface.tools if t.name in old_map]
    if common_old != common_new:
        events.append(DriftEvent(kind=DriftKind.reordered))

    return events
