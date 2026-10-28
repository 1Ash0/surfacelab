"""EXP-001 analysis: position effect from recorded cassettes (offline, replay only).

Follows docs/experiments/EXP-001.md. Deviations are listed in the output JSON.
Writes results/exp001_analysis.json.
"""

from __future__ import annotations

import json
import random
from itertools import combinations
from pathlib import Path

from surfacelab.cases import CaseKind, load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.render import render
from surfacelab.stats import cochrans_q, mcnemar_test
from surfacelab.surface import load_fixture_surface
from surfacelab.variants import balanced_permutations

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
SURFACES = [("goodserver", "fixtures/cases/core.jsonl", 120), ("siblings", "fixtures/cases/siblings.jsonl", 24)]
N_RESAMPLES, SEED = 10_000, 42


def third(idx: int, n: int) -> int:
    return idx * 3 // n  # n=5 -> {0,1},{2,3},{4}; n=4 -> {0,1},{2},{3}


def collect() -> list[dict]:
    store = CassetteStore(Path("cassettes"), mode="replay")
    rows: list[dict] = []
    for model in MODELS:
        prov = OpenAICompatProvider(provider_slug="groq", model_id=model, cassette_store=store)
        for surface_name, cases_path, k in SURFACES:
            variants = balanced_permutations(load_fixture_surface(surface_name), k)
            for case in load_cases(Path(cases_path)):
                if case.kind == CaseKind.abstain:
                    continue  # no gold tool, so no position
                gold = next(iter(case.gold))
                for vi, v in enumerate(variants):
                    names = [t.name for t in v.tools]
                    assert [t["function"]["name"] for t in render(v)] == names, "render reordered tools"
                    emitted = prov.call(case, v)
                    rows.append(dict(model=model, surface=surface_name, case=case.id, variant=vi,
                                     pos=names.index(gold), n=len(names), emitted=emitted,
                                     correct=emitted == gold))
    return rows


def acc(trials: list[dict]) -> float:
    return sum(t["correct"] for t in trials) / len(trials) if trials else float("nan")


def gap(fams: dict[str, list[dict]], lo: int = 0, hi: int = 2, key=lambda t: third(t["pos"], t["n"])) -> float:
    ts = [t for f in fams.values() for t in f]
    return acc([t for t in ts if key(t) == lo]) - acc([t for t in ts if key(t) == hi])


def boot(stat, groups: list[dict[str, list[dict]]]) -> dict:
    """Clustered bootstrap: resample case families (with replacement) within each group."""
    rng = random.Random(SEED)
    point = stat(*groups)
    est = []
    for _ in range(N_RESAMPLES):
        resampled = []
        for g in groups:
            ids = rng.choices(list(g), k=len(g))
            resampled.append({f"{i}#{j}": g[c] for j, c in enumerate(ids) for i in [c]})
        est.append(stat(*resampled))
    est.sort()
    return dict(point=point, lower=est[int(0.025 * N_RESAMPLES)], upper=est[int(0.975 * N_RESAMPLES) - 1])


def families(rows: list[dict], **where) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        if all(r[k] == v for k, v in where.items()):
            out.setdefault(f"{r['surface']}:{r['case']}", []).append(r)
    return out


def flip_rate(trials: list[dict]) -> float:
    pairs = list(combinations([t["emitted"] for t in trials], 2))
    return sum(a != b for a, b in pairs) / len(pairs)


def main() -> None:
    rows = collect()
    out: dict = {"n_trials": len(rows), "n_resamples": N_RESAMPLES, "seed": SEED, "per_model": {}}
    for m in MODELS:
        fams = families(rows, model=m)
        res = {"n_families": len(fams),
               "bin_accuracy": {b: acc([t for f in fams.values() for t in f if third(t["pos"], t["n"]) == b]) for b in range(3)},
               "gap_first_minus_last_third": boot(gap, [fams]),
               "gap_first_minus_last_slot": boot(lambda f: gap(f, 0, 1, key=lambda t: 0 if t["pos"] == 0 else 1 if t["pos"] == t["n"] - 1 else -1), [fams])}
        for s, _, _ in SURFACES:
            sf = families(rows, model=m, surface=s)
            res[f"gap_third_{s}"] = boot(gap, [sf])
        res["H2_gap_siblings_minus_goodserver"] = boot(lambda a, b: gap(a) - gap(b),
                                                       [families(rows, model=m, surface="siblings"), families(rows, model=m, surface="goodserver")])
        # Exploratory: Cochran's Q needs binary cells; cell = family is majority-correct in that bin.
        matrix = [[acc([t for t in f if third(t["pos"], t["n"]) == b]) >= 0.5 for b in range(3)] for f in fams.values()]
        q, df = cochrans_q(matrix)
        res["cochrans_q_exploratory"] = {"Q": q, "df": df, "binarization": "family majority-correct per bin"}
        res["flip_rate_per_case"] = {c: flip_rate(f) for c, f in fams.items()}
        out["per_model"][m] = res

    a, b = families(rows, model=MODELS[0]), families(rows, model=MODELS[1])
    out["H3_gap_20b_minus_120b"] = boot(lambda x, y: gap(x) - gap(y), [a, b])
    key = {(r["surface"], r["case"], r["variant"]): r["correct"] for r in rows if r["model"] == MODELS[1]}
    small = [(r["correct"], key[(r["surface"], r["case"], r["variant"])]) for r in rows if r["model"] == MODELS[0]]
    mc = mcnemar_test(sum(s and not l for s, l in small), sum(l and not s for s, l in small))
    out["H3_mcnemar_matched_trials"] = {"n_20b_only": mc.n_ab, "n_120b_only": mc.n_ba, "p_value": mc.p_value,
                                        "caveat": "treats trials as independent; tests accuracy, not position effect"}
    out["deviations"] = [
        "temperature was not set in any request (provider default), not fixed as the plan assumed",
        "position thirds of 4/5 tools binned by floor(3*index/n); slot-0 vs last-slot reported as sensitivity",
        "3 abstain cases have no gold tool and are excluded: 20 families, not 23",
        "H3 McNemar run on matched (case, permutation) trials; bootstrap gap difference added as the direct H3 test",
        "5 trials where the model declined or emitted malformed calls are scored incorrect (restored from first-pass logs)",
    ]
    Path("results/exp001_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({m: {k: v for k, v in r.items() if k != "flip_rate_per_case"} for m, r in out["per_model"].items()}, indent=1))
    print("H3 gap diff:", out["H3_gap_20b_minus_120b"]); print("H3 McNemar:", out["H3_mcnemar_matched_trials"])


if __name__ == "__main__":
    main()
