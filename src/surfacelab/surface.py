"""Surface loader: construct a Surface from fixture, snapshot, or live server.

Three sources:
  fixture  — read a hand-authored JSON file from fixtures/surfaces/
  snapshot — reconstruct from a Snapshot JSON saved by snapshot.py
  live     — spawn a real MCP server via mcpclient (async; not for CI tests)

apply_variant() delegates to variants.py and is the only place a Surface is
transformed before passing to the runner — it returns a new Surface and never
mutates the input.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from .mcpclient import fetch_surface
from .schema import Surface, Tool
from .snapshot import surface_hash as _surface_hash  # re-export for callers
from .variants import all_permutations, balanced_permutations, permute

# Public re-export so callers can do `from surfacelab.surface import surface_hash`.
__all__ = [
    "SurfaceLoadError",
    "apply_variant",
    "load_fixture_surface",
    "load_live_surface",
    "load_snapshot_surface",
    "surface_hash",
]

surface_hash = _surface_hash  # re-export


class SurfaceLoadError(Exception):
    """Raised when a surface cannot be loaded from the requested source.

    Wraps the underlying OS/JSON error as __cause__ so the stack trace
    always points back to the original failure.
    """


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _default_fixtures_dir() -> Path:
    # Project root / fixtures / surfaces
    return Path(__file__).parent.parent.parent / "fixtures" / "surfaces"


def load_fixture_surface(name: str, fixtures_dir: Path | None = None) -> Surface:
    """Load a Surface from fixtures/surfaces/<name>.json.

    The fixture file is a plain JSON object: {"server_name": ..., "tools": [...]}.
    """
    base = fixtures_dir if fixtures_dir is not None else _default_fixtures_dir()
    path = base / f"{name}.json"
    if not path.exists():
        raise SurfaceLoadError(
            f"Fixture surface {name!r} not found at {path}. "
            f"Create it or check the fixtures_dir argument."
        ) from FileNotFoundError(str(path))
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SurfaceLoadError(f"Could not read fixture {path}: {exc}") from exc
    try:
        return Surface.model_validate(data)
    except Exception as exc:
        raise SurfaceLoadError(f"Invalid fixture schema in {path}: {exc}") from exc


def load_snapshot_surface(path: Path) -> Surface:
    """Reconstruct a Surface from a Snapshot JSON file (as saved by SnapshotStore)."""
    if not path.exists():
        raise SurfaceLoadError(
            f"Snapshot file not found: {path}"
        ) from FileNotFoundError(str(path))
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SurfaceLoadError(f"Could not read snapshot {path}: {exc}") from exc
    try:
        raw_tools: list[dict[str, Any]] = data["surface"]["tools"]
        server_name: str = data["server_name"]
        tools = [
            Tool.model_validate({"name": t["name"], "description": t.get("description", ""),
                                  "inputSchema": t.get("input_schema") or {}})
            for t in raw_tools
        ]
        return Surface(server_name=server_name, tools=tools)
    except (KeyError, TypeError) as exc:
        raise SurfaceLoadError(f"Unexpected snapshot schema in {path}: {exc}") from exc


def load_live_surface(
    command: list[str],
    server_name: str,
    timeout: float = 10.0,
) -> Surface:
    """Spawn a real MCP server and return its Surface (synchronous wrapper).

    Not for use in CI tests — requires a real server command. Wraps the async
    mcpclient.fetch_surface with a wall-clock timeout.
    """
    async def _run() -> Surface:
        return await asyncio.wait_for(
            fetch_surface(command, server_name),
            timeout=timeout,
        )
    try:
        return asyncio.run(_run())
    except TimeoutError as exc:
        raise SurfaceLoadError(
            f"Server {server_name!r} did not respond within {timeout}s"
        ) from exc
    except Exception as exc:
        raise SurfaceLoadError(
            f"Failed to fetch surface from {command}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Variant application
# ---------------------------------------------------------------------------


def apply_variant(surface: Surface, factor: str, **kwargs: Any) -> Surface:
    """Apply a named variant factor and return a new Surface. Never mutates input.

    Supported factors:
      permute            seed=<int>          single seeded shuffle
      all_permutations   (no kwargs)         all N! orderings → first one returned
      balanced           k=<int>, seed=<int> balanced sample of k permutations → first
    """
    if factor == "permute":
        seed: int = int(kwargs.get("seed", 0))
        return permute(surface, seed)
    if factor == "all_permutations":
        perms = all_permutations(surface)
        return perms[0] if perms else surface
    if factor == "balanced":
        k: int = int(kwargs.get("k", 1))
        seed_b: int = int(kwargs.get("seed", 42))
        perms_b = balanced_permutations(surface, k, seed=seed_b)
        return perms_b[0] if perms_b else surface
    raise ValueError(
        f"Unknown variant factor {factor!r}. "
        f"Supported: 'permute', 'all_permutations', 'balanced'."
    )
