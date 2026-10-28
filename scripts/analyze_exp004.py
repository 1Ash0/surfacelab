"""EXP-004 analysis: cross-server collision and namespacing (offline replay + cached embeddings).

Follows docs/experiments/EXP-004.md. Classifies each answer from the emitted tool
name itself, because the built-in grader compares against server-qualified gold
names and so cannot score the `none` and `prefix` conditions.
Writes results/exp004_analysis.json.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from dotenv import load_dotenv
from scipy.stats import spearmanr

from surfacelab.cases import load_cases
from surfacelab.embed import EmbedStore
from surfacelab.similarity import similarity_matrix
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.stats import holm_correction, mcnemar_test, wilson_interval
from surfacelab.surface import load_fixture_surface

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
SURFACES = ["merged_none", "merged_prefix", "merged_qualified"]
EMBEDDERS = [("openrouter", "openai/text-embedding-3-small"), ("gemini", "gemini-embedding-001")]
N_PERM, SEED = 10_000, 42


def qualified_names() -> list[str]:
    return [t.name for t in load_fixture_surface("merged_qualified").tools]


def to_qualified(surface: str, name: str | None) -> str | None:
    if name is None:
        return None
    if surface == "merged_qualified":
        return name
    for q in qualified_names():
        server, tool = q.split("/")
        if name == (tool if surface == "merged_none" else f"{server}_{tool}"):
            return q
    return f"?/{name}"  # unknown name: counted as a wrong-server answer


def classify(gold: str, emitted: str | None) -> str:
    if emitted is None:
        return "miss"
    if emitted == gold:
        return "hit"
    return "within_server" if emitted.split("/")[0] == gold.split("/")[0] else "collision"


def spearman_perm(x: list[float], y: list[float]) -> dict:
    rho = float(spearmanr(x, y).statistic)
    if rho != rho:  # nan: one input is constant (e.g. no confusions observed), so untestable
        return {"rho": None, "p_permutation": None, "n_pairs": len(x), "untestable": "an input is constant"}
    rng = random.Random(SEED)
    ys, extreme = list(y), 0
    for _ in range(N_PERM):
        rng.shuffle(ys)
        r = spearmanr(x, ys).statistic
        extreme += abs(r) >= abs(rho) if r == r else 0  # skip nan (constant input)
    return {"rho": rho, "p_permutation": (extreme + 1) / (N_PERM + 1), "n_pairs": len(x)}


def main() -> None:
    load_dotenv(Path(".env"))
    cases = load_cases(Path("fixtures/cases/cross_server.jsonl"))
    store = CassetteStore(Path("cassettes"), mode="replay")
    rows = []
    for m in MODELS:
        p = OpenAICompatProvider(provider_slug="groq", model_id=m, cassette_store=store, temperature=0.0)
        for s in SURFACES:
            surf = load_fixture_surface(s)
            for c in cases:
                gold = next(iter(c.gold))
                emitted = to_qualified(s, p.call(c, surf))
                rows.append({"model": m, "surface": s, "case": c.id, "gold": gold, "emitted": emitted,
                             "outcome": classify(gold, emitted)})

    out: dict = {"temperature": 0.0, "per_model": {}, "trials": rows}
    for m in MODELS:
        res: dict = {}
        for s in SURFACES:
            rs = [r for r in rows if r["model"] == m and r["surface"] == s]
            k = sum(r["outcome"] == "collision" for r in rs)
            lo, hi = wilson_interval(k, len(rs))
            res[s] = {"n": len(rs), "collisions": k, "collision_rate": k / len(rs), "wilson_95": [lo, hi],
                      "outcomes": {o: sum(r["outcome"] == o for r in rs) for o in ["hit", "collision", "within_server", "miss"]}}
        res["H1_confirmed"] = res["merged_none"]["wilson_95"][0] > 0.10

        def paired(a: str, b: str) -> dict:
            col = {(r["surface"], r["case"]): r["outcome"] == "collision" for r in rows if r["model"] == m}
            mc = mcnemar_test(sum(col[(a, c.id)] and not col[(b, c.id)] for c in cases),
                              sum(col[(b, c.id)] and not col[(a, c.id)] for c in cases))
            return {f"{a}_only_collides": mc.n_ab, f"{b}_only_collides": mc.n_ba, "p_value": mc.p_value}

        res["H2_none_vs_prefix"] = paired("merged_none", "merged_prefix")
        res["H4_prefix_vs_qualified_exploratory"] = paired("merged_prefix", "merged_qualified")
        out["per_model"][m] = res

    # H3: description similarity vs cross-server confusion in the `none` condition, both models pooled.
    names = qualified_names()
    surf = load_fixture_surface("merged_qualified")
    none_rows = [r for r in rows if r["surface"] == "merged_none"]
    gold_tools = sorted({r["gold"] for r in none_rows})
    pairs = [(g, t) for g in gold_tools for t in names if t.split("/")[0] != g.split("/")[0]]
    confusion = []
    for g, t in pairs:
        trials = [r for r in none_rows if r["gold"] == g]
        confusion.append(sum(r["emitted"] == t for r in trials) / len(trials))
    out["H3"] = {"n_cross_server_pairs": len(pairs), "n_pairs_with_any_confusion": sum(c > 0 for c in confusion)}
    for prov, model in EMBEDDERS:
        sim = similarity_matrix(EmbedStore(prov, model, Path("cassettes/embed")).embed_surface(surf))
        x = [sim[names.index(g)][names.index(t)] for g, t in pairs]
        out["H3"][model] = spearman_perm(x, confusion)

    h3_p = out["H3"][EMBEDDERS[0][1]]["p_permutation"]
    for m in MODELS:
        tests = {"H2": out["per_model"][m]["H2_none_vs_prefix"]["p_value"]}
        if h3_p is not None:
            tests["H3"] = h3_p
        out["per_model"][m]["holm_rejects"] = dict(zip(tests, holm_correction(list(tests.values()))))

    Path("results/exp004_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "trials"}, indent=1))


if __name__ == "__main__":
    main()
