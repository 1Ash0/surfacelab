"""Build the Observatory's data file from recorded results (replay only, no API calls).

Writes docs/design/observatory-data.json with, for every EXP-013 tool: full description split
into token-weighted segments, its nearest neighbours by description embedding, and for every
recorded trial the raw first call from the cassette (tool name and arguments, or the failed
generation). Also the confusion pairs with their similarity percentile, the experiment archive
and the determinism probe.

  PYTHONPATH=scripts python scripts/build_observatory_data.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import tiktoken
from dotenv import load_dotenv

from run_followups import plan_013
from surfacelab.cases import load_cases
from surfacelab.embed import EmbedStore
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.render import render
from surfacelab.schema import Surface

LOADOUTS = ["browser", "web", "workspace", "docs"]
MODELS = {"20b": "openai/gpt-oss-20b", "120b": "openai/gpt-oss-120b", "27b": "qwen/qwen3.8-27b"}
ENC = tiktoken.get_encoding("o200k_base")


def segments(desc: str, schema: dict) -> list[list]:
    parts = [s for s in re.split(r"(?<=[.!?:])\s+|\n+", desc.strip()) if s.strip()]
    segs = [[s.strip(), len(ENC.encode(s))] for s in parts]
    segs.append(["input schema (parameters)", len(ENC.encode(json.dumps(schema)))])
    return segs


def main() -> None:
    load_dotenv(Path(".env"))
    store = EmbedStore("openrouter", "openai/text-embedding-3-small", Path("cassettes/embed"))
    tools, vecs, key = [], [], {}
    for L in LOADOUTS:
        s = Surface.model_validate_json(Path(f"fixtures/surfaces/real_{L}.json").read_text())
        own = json.loads(Path(f"fixtures/surfaces/real_{L}.servers.json").read_text())
        for t, rnd, v in zip(s.tools, render(s), store.embed_surface(s)):
            key[(L, t.name)] = len(tools)
            tools.append({"n": t.name, "s": own[t.name], "l": L, "k": len(ENC.encode(json.dumps(rnd))),
                          "d": " ".join(t.description.split()), "seg": segments(t.description, t.input_schema)})
            vecs.append(v)
    X = np.array(vecs); X = X / np.linalg.norm(X, axis=1, keepdims=True)
    sim = X @ X.T
    try:  # UMAP spreads near neighbours more legibly than PCA; fall back when it is not installed
        import umap
        P = umap.UMAP(n_components=3, metric="cosine", n_neighbors=10, min_dist=0.35, random_state=42).fit_transform(X)
        P = P - P.mean(0); layout = "umap (cosine, 10 neighbours, seed 42)"
    except ImportError:
        Xc = X - X.mean(0); _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
        P = Xc @ Vt[:3].T; layout = "pca"
    P = P / np.abs(P).max(0)
    for i, t in enumerate(tools):
        t["p"] = [round(float(x), 3) for x in P[i]]
        same = [j for j in range(len(tools)) if j != i and tools[j]["l"] == t["l"]]
        t["nb"] = [[j, round(float(sim[i, j]), 3)] for j in sorted(same, key=lambda j: -sim[i, j])[:4]]

    cases = {c.id: c for c in load_cases(Path("fixtures/cases/real_loadouts.jsonl"))}
    cassettes = CassetteStore(Path("cassettes"), mode="replay")
    trials, raw = [], {}
    for mk, mid in MODELS.items():
        prov = OpenAICompatProvider(provider_slug="groq", model_id=mid, cassette_store=cassettes, temperature=0.0)
        for label, cs, (variant,) in plan_013():
            for c in cs:
                req = prov._build_request(c, variant)
                resp = cassettes.get(prov._request_bytes(req))
                msg = (resp.get("choices") or [{}])[0].get("message") or {}
                calls = msg.get("tool_calls") or []
                name = calls[0]["function"]["name"] if calls else None
                args = calls[0]["function"].get("arguments", "") if calls else ""
                e = key.get((label["loadout"], name)) if name else None
                trials.append([mk, c.id, label["rotation"], e, 1 if name in c.gold else 0])
                raw[f"{mk}|{c.id}|{label['rotation']}"] = {
                    "name": name, "args": (args or "")[:400], "failed": bool(resp.get("surfacelab_tool_use_failed")),
                    "text": (msg.get("content") or "")[:400], "extra_calls": max(0, len(calls) - 1)}

    # gold is a set: sort so the file is identical on every run
    case_out = {i: {"q": c.request, "l": c.surface_name[5:], "g": sorted(key[(c.surface_name[5:], g)] for g in c.gold),
                    "sh": c.note.startswith("[shared]")} for i, c in cases.items()}
    pairs: dict = {}
    # attribute each wrong call to the accepted tool most similar to it (same rule as EXP-013 H4)
    for tr in trials:
        m, cid, rot, e, ok = tr
        if ok or e is None:
            tr.append(None); continue
        g = max(case_out[cid]["g"], key=lambda j: sim[j, e])
        tr.append(g)
        pairs.setdefault(f"{g}-{e}", {"a": g, "b": e, "n": 0, "by": {}})
        pairs[f"{g}-{e}"]["n"] += 1
        pairs[f"{g}-{e}"]["by"][m] = pairs[f"{g}-{e}"]["by"].get(m, 0) + 1
    for pr in pairs.values():
        a, b = pr["a"], pr["b"]
        others = [j for j in range(len(tools)) if tools[j]["l"] == tools[a]["l"] and j != a]
        pr["cos"] = round(float(sim[a, b]), 3)
        pr["pct"] = round(sum(sim[a, j] < sim[a, b] for j in others) / max(1, len(others)), 3)

    det = json.loads(Path("results/determinism_probe.json").read_text())
    out = {"layout": layout, "tools": tools, "trials": trials, "cases": case_out, "raw": raw, "pairs": list(pairs.values()),
           "det": {k.split("/")[-1].replace("gpt-oss-", ""): v["groups"] for k, v in det["models"].items()},
           "exps": json.loads(Path("docs/design/observatory-archive.json").read_text(encoding="utf-8")),
           "sib_t0": {m.split("-")[-1]: v["bin_accuracy"] for m, v in
                      json.loads(Path("results/exp001_siblings_t0_analysis.json").read_text())["per_model"].items()}}
    Path("docs/design/observatory-data.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"tools {len(tools)} trials {len(trials)} raw {len(raw)} pairs {len(pairs)}")


if __name__ == "__main__":
    main()
