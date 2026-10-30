"""EXP-006 second probe (drift): same servers and sandbox, images rebuilt from each package's latest release.

Only initialize + tools/list are sent (ADR-008), inside probe_docker() (ADR-022). New snapshots go to
runs/exp006-drift/snapshots; they are compared with the committed 2026-10-28 snapshots by classify_drift().

  python scripts/run_exp006_drift.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import run_exp006 as base

from surfacelab.pulse import probe_docker
from surfacelab.snapshot import SnapshotStore, classify_drift

NODE_NEW, PY_NEW, GH_NEW = "surfacelab/exp006-node:drift", "surfacelab/exp006-py:drift", "ghcr.io/github/github-mcp-server:latest"
SWAP = {base.NODE: NODE_NEW, base.PY: PY_NEW, base.GH: GH_NEW}
OLD, NEW = Path("runs/exp006/snapshots"), Path("runs/exp006-drift/snapshots")


NODE_VERSIONS = (
    "const fs=require('fs');const o={};for(const d of fs.readdirSync('/opt')){"
    "const deps=JSON.parse(fs.readFileSync('/opt/'+d+'/package.json')).dependencies||{};"
    "for(const n of Object.keys(deps)){o[d]=n+'@'+JSON.parse(fs.readFileSync('/opt/'+d+'/node_modules/'+n+'/package.json')).version}}"
    "console.log(JSON.stringify(o))"
)


def installed_versions() -> dict[str, object]:
    """Versions inside the drift images, read with no network."""
    node = subprocess.run(["docker", "run", "--rm", "--network=none", NODE_NEW, "node", "-e", NODE_VERSIONS],
                          capture_output=True, text=True, check=False).stdout
    py = subprocess.run(["docker", "run", "--rm", "--network=none", PY_NEW, "pip", "freeze"],
                        capture_output=True, text=True, check=False).stdout
    wanted = ("mcp-server-git", "mcp-server-fetch", "mcp-server-time", "awslabs.aws-documentation-mcp-server")
    return {"npm": json.loads(node) if node.strip() else {},
            "pip": {ln.split("==")[0]: ln.split("==")[1] for ln in py.splitlines() if "==" in ln and ln.split("==")[0] in wanted}}


def run(name: str, timeout: float, store: SnapshotStore) -> dict:
    image, cmd, env = base.COMMANDS[name]
    flags = ["-e", "HOME=/tmp"] + [a for v in env for a in ("-e", f"{v}={base.PLACEHOLDER}")]
    r = probe_docker(SWAP[image], cmd, name, timeout=timeout, snapshot_store=store, extra_docker_flags=flags)
    return {"server": name, "timeout_s": timeout, "outcome": r.outcome.value,
            "n_tools": len(r.surface.tools) if r.surface else 0,
            "error": (r.error_message or "")[:300], "instruction_like_flags": [str(f) for f in r.instruction_like_flags]}


def main() -> None:
    targets = [t["name"] for t in json.loads(Path("fixtures/targets/exp006_targets.json").read_text())["targets"]]
    old_store, new_store = SnapshotStore(OLD), SnapshotStore(NEW)
    first = json.loads(Path("results/exp006.json").read_text())
    first_out = {r["server"]: r["outcome"] for r in first["primary"]}
    primary = []
    for name in targets:
        primary.append(run(name, 10.0, new_store))
        print(f"  {name:20} {primary[-1]['outcome']:18} tools={primary[-1]['n_tools']}", flush=True)
    retry = [run(r["server"], 30.0, new_store) for r in primary if r["outcome"] == "timeout"]
    for r in retry:
        print(f"  retry 30s {r['server']:20} {r['outcome']:18} tools={r['n_tools']}", flush=True)
    drift = []
    for name in targets:
        try:
            old, new = old_store.load_latest(name), new_store.load_latest(name)
        except (FileNotFoundError, KeyError, ValueError):
            drift.append({"server": name, "status": "no_pair"})
            continue
        ev = classify_drift(old, new)
        drift.append({"server": name, "status": "compared", "old_hash": old.surface_hash, "new_hash": new.surface_hash,
                      "old_tools": len(old.surface.tools), "new_tools": len(new.surface.tools),
                      "events": [{"kind": e.kind.value, "tool": e.tool_name} for e in ev]})
    out = {"probed": "2026-10-31", "first_probe": "2026-10-28",
           "outcome_changes": {r["server"]: [first_out.get(r["server"]), r["outcome"]]
                               for r in primary if first_out.get(r["server"]) != r["outcome"]},
           "primary": primary, "snapshot_retry_30s_not_primary": retry, "drift": drift,
           "versions": installed_versions()}
    Path("results/exp006_drift.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    changed = [d for d in drift if d["status"] == "compared" and d["events"] and d["events"][0]["kind"] != "unchanged"]
    print(f"drift in {len(changed)} of {len(drift)} servers; outcome changes: {len(out['outcome_changes'])}")


if __name__ == "__main__":
    main()
