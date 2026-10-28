"""EXP-006 runner: sandboxed handshake probe of the curated list (docs/experiments/EXP-006.md).

Only initialize + tools/list are sent (ADR-008), inside probe_docker() (ADR-022). Servers that
demand a credential to start get the literal placeholder below; the container has no network.
The primary outcome uses the preregistered 10 s timeout. Servers that time out are probed once
more at 30 s purely to collect snapshots for EXP-013; that pass is reported separately.

  python scripts/run_exp006.py
"""

from __future__ import annotations

import json
from pathlib import Path

from surfacelab.pulse import probe_docker
from surfacelab.snapshot import SnapshotStore
from surfacelab.stats import wilson_interval

PLACEHOLDER = "surfacelab-placeholder"
NODE, PY, GH = "surfacelab/exp006-node:1", "surfacelab/exp006-py:1", (
    "ghcr.io/github/github-mcp-server@sha256:250bc6ce70788207608ef74cef4397230ff2e8481218da74d6093e4bd9101132")


def bin_(name: str, exe: str) -> list[str]:
    return [f"/opt/{name}/node_modules/.bin/{exe}"]


# name -> (image, command, env vars set to the placeholder)
COMMANDS: dict[str, tuple[str, list[str], list[str]]] = {
    "filesystem": (NODE, bin_("filesystem", "mcp-server-filesystem") + ["/tmp"], []),
    "memory": (NODE, bin_("memory", "mcp-server-memory"), []),
    "sequential-thinking": (NODE, bin_("sequential-thinking", "mcp-server-sequential-thinking"), []),
    "git": (PY, ["mcp-server-git"], []),
    "fetch": (PY, ["mcp-server-fetch"], []),
    "time": (PY, ["mcp-server-time"], []),
    "aws-documentation": (PY, ["awslabs.aws-documentation-mcp-server"], []),
    "github": (GH, ["stdio"], ["GITHUB_PERSONAL_ACCESS_TOKEN"]),
    "notion": (NODE, bin_("notion", "notion-mcp-server"), ["NOTION_TOKEN"]),
    "playwright": (NODE, bin_("playwright", "playwright-mcp"), []),
    "chrome-devtools": (NODE, bin_("chrome-devtools", "chrome-devtools-mcp"), []),
    "brave-search": (NODE, bin_("brave-search", "brave-search-mcp-server"), ["BRAVE_API_KEY"]),
    "tavily": (NODE, bin_("tavily", "tavily-mcp"), ["TAVILY_API_KEY"]),
    "firecrawl": (NODE, bin_("firecrawl", "firecrawl-mcp"), ["FIRECRAWL_API_KEY"]),
    "supabase": (NODE, bin_("supabase", "mcp-server-supabase") + [f"--access-token={PLACEHOLDER}"], []),
    "neon": (NODE, bin_("neon", "mcp-server-neon") + ["start", PLACEHOLDER], []),
    "mongodb": (NODE, bin_("mongodb", "mongodb-mcp-server"), []),
    "stripe": (NODE, bin_("stripe", "mcp") + ["--tools=all", f"--api-key={PLACEHOLDER}"], []),
    "context7": (NODE, bin_("context7", "context7-mcp"), []),
}


def run(name: str, timeout: float, store: SnapshotStore | None) -> dict:
    image, cmd, env = COMMANDS[name]
    flags = ["-e", "HOME=/tmp"] + [a for v in env for a in ("-e", f"{v}={PLACEHOLDER}")]
    r = probe_docker(image, cmd, name, timeout=timeout, snapshot_store=store, extra_docker_flags=flags)
    return {"server": name, "timeout_s": timeout, "outcome": r.outcome.value,
            "n_tools": len(r.surface.tools) if r.surface else 0,
            "error": (r.error_message or "")[:300], "instruction_like_flags": [str(f) for f in r.instruction_like_flags]}


def main() -> None:
    targets = [t["name"] for t in json.loads(Path("fixtures/targets/exp006_targets.json").read_text())["targets"]]
    assert set(targets) == set(COMMANDS), "every target needs exactly one command"
    store = SnapshotStore(Path("runs/exp006/snapshots"))
    primary = []
    for name in targets:
        primary.append(run(name, 10.0, store))
        print(f"  {name:20} {primary[-1]['outcome']:18} tools={primary[-1]['n_tools']}", flush=True)
    ok = sum(r["outcome"] == "ok" for r in primary)
    lo, hi = wilson_interval(ok, len(primary))
    retry = [run(r["server"], 30.0, store) for r in primary if r["outcome"] == "timeout"]
    for r in retry:
        print(f"  retry 30s {r['server']:20} {r['outcome']:18} tools={r['n_tools']}", flush=True)
    out = {"n": len(primary), "ok": ok, "ok_rate": ok / len(primary), "wilson": [lo, hi],
           "by_outcome": {o: sum(r["outcome"] == o for r in primary) for o in sorted({r["outcome"] for r in primary})},
           "primary": primary, "snapshot_retry_30s_not_primary": retry}
    Path("results/exp006.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"ok {ok}/{len(primary)} [{lo:.2f}, {hi:.2f}]")


if __name__ == "__main__":
    main()
