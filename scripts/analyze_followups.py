"""Analysis for EXP-010, EXP-011, EXP-012 as preregistered. Reads results/exp0NN_<model>.json
written by run_followups.py; no API calls. Writes results/exp0NN_analysis.json.

  python scripts/analyze_followups.py --exp 11
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import tiktoken

from analyze_exp005 import logistic_slope
from run_followups import ND
from surfacelab.cases import load_cases
from surfacelab.render import render
from surfacelab.stats import holm_correction, mcnemar_test, wilson_interval
from surfacelab.surface import load_fixture_surface

MODELS = ["20b", "120b", "27b"]  # 27b = qwen/qwen3.8-27b (EXP-014); missing files are skipped
N_RESAMPLES, SEED = 10_000, 42


def load(exp: int, m: str) -> list[dict] | None:
    p = Path(f"results/exp0{exp}_{m}.json")
    return json.loads(p.read_text(encoding="utf-8"))["trials"] if p.exists() else None


def fams(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["case_id"], []).append(r)
    return out


def acc(rows: list[dict]) -> float:
    return sum(r["correct"] for r in rows) / len(rows) if rows else float("nan")


def boot(stat, groups: dict[str, list[dict]], need_valid: bool = False) -> dict:
    """Clustered bootstrap over families; stat takes a list of trial rows (or returns None)."""
    rng, ids = random.Random(SEED), sorted(groups)
    point = stat([r for i in ids for r in groups[i]])
    est = []
    for _ in range(N_RESAMPLES):
        v = stat([r for i in rng.choices(ids, k=len(ids)) for r in groups[i]])
        if v is not None:
            est.append(v)
    if point is None or (need_valid and len(est) < 0.9 * N_RESAMPLES):
        return {"point": point, "lower": None, "upper": None, "note": "not estimable"}
    est.sort()
    k = len(est)
    return {"point": point, "lower": est[int(0.025 * k)], "upper": est[int(0.975 * k) - 1]}


# ---- EXP-010 ---------------------------------------------------------------

def held_out() -> set[str]:
    """One case per tool, chosen by random.Random(42), surfaces and tools in canonical order."""
    rng, cases, out = random.Random(42), load_cases(Path("fixtures/cases/near_dup.jsonl")), set()
    for s in ND:
        for t in load_fixture_surface(s).tools:
            pair = sorted(c.id for c in cases if c.surface_name == s and t.name in c.gold)
            out.add(rng.choice(pair))
    return out


def tokens(name: str) -> int:
    enc = tiktoken.get_encoding("o200k_base")
    return sum(len(enc.encode(t.description)) for t in load_fixture_surface(name).tools)


def exp010() -> dict:
    ho, out = held_out(), {"held_out": sorted(ho), "models": {}}
    rise = {e: sum(tokens(f"{s}_{e}") for s in ND) / sum(tokens(s) for s in ND) - 1 for e in ["contrast", "negation"]}
    out["description_token_rise"] = rise
    for m in MODELS[:2]:
        rows = load(10, m)
        if rows is None:
            out["models"][m] = "not run (ceiling check, see EXP-010.md)"
            continue
        rows = [r for r in rows if r["case_id"] in ho]
        res, pvals = {"base_accuracy": acc([r for r in rows if r["condition"] == "base"])}, []
        for e in ["contrast", "negation"]:
            def delta(rs, e=e):
                return acc([r for r in rs if r["condition"] == e]) - acc([r for r in rs if r["condition"] == "base"])
            ci = boot(delta, fams(rows))
            key = lambda r: (r["case_id"], r["variant_index"])
            base = {key(r): r["correct"] for r in rows if r["condition"] == "base"}
            ed = {key(r): r["correct"] for r in rows if r["condition"] == e}
            mc = mcnemar_test(sum(ed[k] and not base[k] for k in base), sum(base[k] and not ed[k] for k in base))
            pvals.append(mc.p_value)
            v = ("helps" if ci["lower"] > 0.05 else "regresses" if ci["upper"] < -0.05
                 else "costs" if ci["lower"] <= 0 <= ci["upper"] and rise[e] > 0.20 else "inconclusive")
            res[e] = {"accuracy": acc([r for r in rows if r["condition"] == e]), "delta": ci,
                      "mcnemar_p": mc.p_value, "verdict": v}
        for e, rej in zip(["contrast", "negation"], holm_correction(pvals)):
            res[e]["holm_reject"] = rej
        out["models"][m] = res
    return out


# ---- EXP-011 ---------------------------------------------------------------

def classify(r: dict, servers: list[str], names: set[str]) -> str:
    e, gold = r["emitted"], r["gold"]
    if e is None:
        return "no_call"
    if e in gold:
        return "hit"
    if e not in names:
        return "nonexistent"

    def split(n: str) -> tuple[str, str]:
        if r["scheme"] == "qualified":
            return tuple(n.split("/"))  # type: ignore[return-value]
        if r["scheme"] == "prefix":
            s = next(s for s in servers if n.startswith(s + "_"))
            return s, n[len(s) + 1:]
        return (servers[1], n[:-2]) if n.endswith("_2") else (servers[0], n)

    (es, et), (gs, gt) = split(e), split(next(iter(gold)))
    return "collision" if et == gt and es != gs else "within_server"


def exp011() -> dict:
    cases = {c.id: c for c in load_cases(Path("fixtures/cases/cross_overlap.jsonl"))}
    out: dict = {"models": {}}
    for m in MODELS:
        rows = load(11, m)
        if rows is None:
            continue
        res: dict = {}
        for r in rows:
            q = load_fixture_surface(f"xo_{r['pair']}_qualified")
            servers = list(dict.fromkeys(t.name.split("/")[0] for t in q.tools))
            sur = load_fixture_surface(f"xo_{r['pair']}_{r['scheme']}")
            from run_followups import _remap
            r["gold"] = {_remap(g, r["scheme"], servers[0]) for g in cases[r["case_id"]].gold}
            r["cls"] = classify(r, servers, {t.name for t in sur.tools})
        for sch in ["none", "prefix", "qualified"]:
            rs = [r for r in rows if r["scheme"] == sch]
            counts = {k: sum(r["cls"] == k for r in rs) for k in
                      ["hit", "collision", "within_server", "nonexistent", "no_call"]}
            lo, hi = wilson_interval(counts["collision"], len(rs))
            fam = fams(rs)
            res[sch] = {"n": len(rs), "counts": counts, "collision_rate": counts["collision"] / len(rs),
                        "wilson": [lo, hi], "nonexistent_rate": counts["nonexistent"] / len(rs),
                        "bootstrap": boot(lambda x: sum(r["cls"] == "collision" for r in x) / len(x), fam)}
        key = lambda r: (r["case_id"], r["variant_index"])
        none = {key(r): r["cls"] == "collision" for r in rows if r["scheme"] == "none"}
        pre = {key(r): r["cls"] == "collision" for r in rows if r["scheme"] == "prefix"}
        mc = mcnemar_test(sum(none[k] and not pre[k] for k in none), sum(pre[k] and not none[k] for k in none))
        res["H1_confirmed"] = res["none"]["wilson"][0] > 0.10
        res["H2"] = {"mcnemar_p": mc.p_value, "n_none_only": mc.n_ab, "n_prefix_only": mc.n_ba,
                     "confirmed": holm_correction([mc.p_value])[0] and mc.n_ab > mc.n_ba}
        res["H3_exploratory"] = {"qualified_nonexistent": res["qualified"]["nonexistent_rate"],
                                 "prefix_nonexistent": res["prefix"]["nonexistent_rate"]}
        out["models"][m] = res
    return out


# ---- EXP-012 ---------------------------------------------------------------

def exp012() -> dict:
    out: dict = {"models": {}}
    for m in MODELS:
        rows = load(12, m)
        if rows is None:
            continue
        n0 = [dict(r, kind=k) for r in rows if r["n"] == 0 for k in ["unrelated", "near-duplicate"]]
        res: dict = {"n0_accuracy": acc([r for r in rows if r["n"] == 0])}
        for k in ["unrelated", "near-duplicate"]:
            rs = n0 + [r for r in rows if r["kind"] == k]
            curve = {n: acc([r for r in rs if r["n"] == n]) for n in [0, 2, 5, 10, 20]}
            slope = boot(lambda x: logistic_slope([r["n"] for r in x], [float(r["correct"]) for r in x]),
                         fams(rs), need_valid=True)
            drop20 = boot(lambda x: acc([r for r in x if r["n"] == 0]) - acc([r for r in x if r["n"] == 20]), fams(rs))
            res[k] = {"accuracy_by_n": curve, "slope_per_10": slope, "drop_0_to_20": drop20}
        nd = res["near-duplicate"]
        res["H1_confirmed"] = (nd["slope_per_10"]["upper"] is not None and nd["slope_per_10"]["upper"] < 0) or (
            nd["slope_per_10"]["upper"] is None and nd["drop_0_to_20"]["lower"] > 0)

        def dd(x):
            d = lambda k: acc([r for r in x if r["n"] == 0]) - acc([r for r in x if r["n"] == 10 and r["kind"] == k])
            return d("near-duplicate") - d("unrelated")
        res["H2"] = boot(dd, fams(rows))
        res["H2"]["confirmed"] = res["H2"]["lower"] > 0.05
        out["models"][m] = res
    out["H1_confirmed_any_model"] = any(v["H1_confirmed"] for v in out["models"].values())
    return out


# ---- EXP-013 ---------------------------------------------------------------

def exp013() -> dict:
    cases = {c.id: c for c in load_cases(Path("fixtures/cases/real_loadouts.jsonl"))}
    owner, order = {}, {}
    for name in ["browser", "web", "workspace", "docs"]:
        own = json.loads(Path(f"fixtures/surfaces/real_{name}.servers.json").read_text())
        owner[name] = own
        order[name] = list(dict.fromkeys(own.values()))
    out: dict = {"models": {}}
    p_h1, p_h2 = [], []
    for m in MODELS:
        rows = load(13, m)
        if rows is None:
            continue
        for r in rows:
            c, own, sv = cases[r["case_id"]], owner[r["loadout"]], order[r["loadout"]]
            rot = sv[r["rotation"]:] + sv[:r["rotation"]]
            accepted = {own[g] for g in c.gold}
            r["shared"] = len(accepted) >= 2
            r["server"] = own.get(r["emitted"]) if r["emitted"] else None
            r["first_accepted"] = next(s for s in rot if s in accepted)  # earliest server that can do it
            r["chance"] = 1 / len(accepted)
        sh = [r for r in rows if r["shared"]]
        un = [r for r in rows if not r["shared"]]

        def excess(x):
            ok = [r for r in x if r["correct"]]
            if not ok:
                return None
            return sum(r["server"] == r["first_accepted"] for r in ok) / len(ok) - sum(r["chance"] for r in ok) / len(ok)

        h1 = boot(excess, fams(sh))
        rng, ids, neg = random.Random(SEED), sorted(fams(sh)), 0
        f_sh = fams(sh)
        for _ in range(N_RESAMPLES):  # one-sided bootstrap p for Holm: share of resamples with excess <= 0
            v = excess([r for i in rng.choices(ids, k=len(ids)) for r in f_sh[i]])
            neg += v is None or v <= 0
        p_h1.append(neg / N_RESAMPLES)
        h2 = boot(acc, fams(un))
        rng, ids, f_un, low = random.Random(SEED), sorted(fams(un)), fams(un), 0
        for _ in range(N_RESAMPLES):
            low += acc([r for i in rng.choices(ids, k=len(ids)) for r in f_un[i]]) < 0.90
        p_h2.append(low / N_RESAMPLES)
        ok = [r for r in sh if r["correct"]]
        flips = {}
        for cid, f in fams(sh).items():
            chosen = {r["server"] for r in f if r["correct"]}
            flips[cid] = len(chosen) > 1
        prefs: dict = {}
        for r in ok:
            prefs.setdefault(r["loadout"], {}).setdefault(r["server"], 0)
            prefs[r["loadout"]][r["server"]] += 1
        by_loadout = {}
        for name in order:
            s = [r for r in ok if r["loadout"] == name]
            if s:
                by_loadout[name] = {"n": len(s), "first_listed_share": sum(r["server"] == r["first_accepted"] for r in s) / len(s),
                                    "chance": sum(r["chance"] for r in s) / len(s)}
        out["models"][m] = {
            "shared": {"trials": len(sh), "accuracy": acc(sh), "correct_trials": len(ok),
                       "first_listed_share": sum(r["server"] == r["first_accepted"] for r in ok) / len(ok) if ok else None,
                       "chance": sum(r["chance"] for r in ok) / len(ok) if ok else None,
                       "excess_over_chance": h1, "by_loadout": by_loadout,
                       "H3_flip_rate": sum(flips.values()) / len(flips), "flipping_cases": sorted(k for k, v in flips.items() if v),
                       "H3_server_counts": prefs},
            "unique": {"trials": len(un), "accuracy": h2,
                       "refusals": sum(r["emitted"] is None for r in un),
                       "errors": [(r["case_id"], r["loadout"], r["rotation"], r["emitted"]) for r in un if not r["correct"]]},
            "H1_verdict": "confirmed" if h1["lower"] is not None and h1["lower"] > 0 else
                          "absent" if h1["upper"] is not None and h1["upper"] < 0.05 else "inconclusive",
            "H2_verdict": "confirmed" if h2["lower"] >= 0.90 else "not_confirmed" if h2["upper"] < 0.90 else "inconclusive",
        }
    for key, ps in [("H1_holm_reject", p_h1), ("H2_holm_reject", p_h2)]:
        for m, rej in zip([m for m in MODELS if m in out["models"]], holm_correction(ps)):
            out["models"][m][key] = rej
            out["models"][m][key.replace("holm_reject", "bootstrap_p")] = ps[[x for x in MODELS if x in out["models"]].index(m)]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", type=int, choices=[10, 11, 12, 13], required=True)
    exp = ap.parse_args().exp
    out = {10: exp010, 11: exp011, 12: exp012, 13: exp013}[exp]()
    Path(f"results/exp0{exp}_analysis.json").write_text(json.dumps(out, indent=1, default=list), encoding="utf-8")
    print(json.dumps(out, indent=1, default=list))


if __name__ == "__main__":
    main()
