"""Build EXP-013 loadouts from sandboxed tools/list probes (docs/experiments/EXP-013.md).

Each server is probed inside probe_docker() exactly as in EXP-006, optionally with the
server's own documented tool-selection option, so tool names, descriptions and schemas are
verbatim. Loadouts are written to fixtures/surfaces/real_<loadout>.json with a sidecar map of
tool -> server, and their rendered size is checked against the free-tier cap.

  python scripts/build_exp013_loadouts.py
"""

from __future__ import annotations

import json
from pathlib import Path

import tiktoken

from run_exp006 import COMMANDS, PLACEHOLDER
from surfacelab.pulse import probe_docker
from surfacelab.render import render
from surfacelab.schema import Surface

# Qwen on Groq has a 7,000 input-tokens-per-minute limit and counted ~1.05x the local o200k JSON size
# (gpt-oss counted ~0.62x), so Qwen binds. measure_exp013_tokens.py checks the real counts.
CAP = 6500  # provider-reported prompt tokens, every model
LOCAL_CAP = 6000

# Server-documented selection options (from each server's --help, 2026-10-28).
OPTIONS: dict[str, list[str]] = {
    "chrome-devtools": ["--categoryEmulation=false", "--categoryPerformance=false",
                        "--categoryMemory=false", "--categoryNetwork=false",
                        "--categoryInput=false", "--categoryDebugging=false"],
    "brave-search": ["--enabled-tools", "brave_web_search", "brave_news_search", "brave_image_search"],
    "github": ["--tools=get_file_contents,create_or_update_file,delete_file,push_files,search_code,"
               "list_commits,get_commit,create_branch,list_branches,search_repositories"],
}

LOADOUTS: dict[str, list[str]] = {
    "browser": ["playwright", "chrome-devtools"],
    "web": ["fetch", "tavily", "brave-search"],
    "workspace": ["filesystem", "github"],
    "docs": ["context7", "aws-documentation", "fetch"],
}


def snapshot(name: str) -> Surface:
    image, cmd, env = COMMANDS[name]
    flags = ["-e", "HOME=/tmp"] + [a for v in env for a in ("-e", f"{v}={PLACEHOLDER}")]
    r = probe_docker(image, cmd + OPTIONS.get(name, []), name, timeout=30.0, extra_docker_flags=flags)
    assert r.surface is not None and r.surface.tools, f"{name}: {r.outcome} {r.error_message}"
    return r.surface


def main() -> None:
    enc = tiktoken.get_encoding("o200k_base")
    cache: dict[str, Surface] = {}
    summary = {}
    for loadout, servers in LOADOUTS.items():
        tools, owner = [], {}
        for s in servers:
            cache.setdefault(s, snapshot(s))
            for t in cache[s].tools:
                assert t.name not in owner, f"name clash {t.name} in {loadout}"
                owner[t.name] = s
                tools.append(t)
        surf = Surface(server_name=f"real_{loadout}", tools=tools)
        n = len(enc.encode(json.dumps(render(surf))))
        summary[loadout] = {"servers": servers, "tools": len(tools), "tokens": n, "within_local_cap": n <= LOCAL_CAP}
        Path(f"fixtures/surfaces/real_{loadout}.json").write_text(surf.model_dump_json(indent=2), encoding="utf-8")
        Path(f"fixtures/surfaces/real_{loadout}.servers.json").write_text(json.dumps(owner, indent=1), encoding="utf-8")
        print(f"{loadout:10} tools={len(tools):3} tokens={n:5} {'ok' if n <= LOCAL_CAP else 'OVER CAP'}", flush=True)
    Path("results/exp013_loadouts.json").write_text(json.dumps({"cap": CAP, "loadouts": summary}, indent=1))


if __name__ == "__main__":
    main()
