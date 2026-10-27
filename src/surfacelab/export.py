"""Export: build web/public/data/ from results/ for the Observatory.

Two artefacts per run:
  index.json          — catalogue of all runs (appended on each export)
  run-<id>.json       — per-run detail: families, trials, Wilson CI

The Galaxy scene reads separate per-surface UMAP files (built by export_galaxy
when embeddings are available). Those are optional — the Observatory degrades
gracefully when they are absent.
"""

from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path
from typing import Any

from .report import ExperimentReport


def _run_id() -> str:
    return f"{int(time.time())}"


def export_run(
    report: ExperimentReport,
    output_dir: Path,
    run_id: str | None = None,
) -> Path:
    """Write a per-run JSON file to output_dir/run-<id>.json.

    Returns the path of the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rid = run_id or _run_id()
    payload: dict[str, Any] = {
        "run_id": rid,
        "exported_at": int(time.time()),
        **dataclasses.asdict(report),
    }
    out = output_dir / f"run-{rid}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def export_index(output_dir: Path) -> Path:
    """(Re)build output_dir/index.json from all run-*.json files in output_dir.

    Scans for every run-<id>.json, reads the minimal summary fields, and writes
    an index sorted newest-first. Safe to call multiple times; idempotent.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []

    for run_file in sorted(output_dir.glob("run-*.json")):
        try:
            data: dict[str, Any] = json.loads(run_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        entries.append({
            "run_id": data.get("run_id", run_file.stem),
            "exported_at": data.get("exported_at", 0),
            "n_cases": data.get("n_cases", 0),
            "n_trials": data.get("n_trials", 0),
            "accuracy": data.get("accuracy", 0.0),
            "ci_lower": data.get("ci_lower", 0.0),
            "ci_upper": data.get("ci_upper", 0.0),
            "file": run_file.name,
        })

    entries.sort(key=lambda e: e["exported_at"], reverse=True)
    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps({"runs": entries}, indent=2), encoding="utf-8")
    return index_path


def export_galaxy(
    surface_name: str,
    coords: list[list[float]],
    tool_names: list[str],
    output_dir: Path,
) -> Path:
    """Write a Galaxy scene JSON for a surface's UMAP projection.

    coords  — list of [x, y, z] from umap_project()
    tool_names — parallel list of tool names (same order as coords)

    The Observatory Galaxy scene reads this file; the caption must say
    'projected position' not 'similarity' (CLAUDE.md rule 11).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    points = [
        {"name": name, "x": c[0], "y": c[1], "z": c[2] if len(c) > 2 else 0.0}
        for name, c in zip(tool_names, coords, strict=True)
    ]
    payload: dict[str, Any] = {
        "surface": surface_name,
        "caption": "projected position (UMAP) — not semantic similarity",
        "points": points,
    }
    out = output_dir / f"galaxy-{surface_name}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
