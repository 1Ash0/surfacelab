"""EXP-005 analysis: accuracy vs distractor count (offline, replay only).

Follows docs/experiments/EXP-005.md. Writes results/exp005_analysis.json.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from run_exp005 import KINDS, NS, cases, conditions  # same surfaces and cases as the run
from surfacelab.grading import Verdict, grade
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.stats import mcnemar_test

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
N_RESAMPLES, SEED = 10_000, 42


def logistic_slope(n: list[float], y: list[float]) -> float | None:
    """Slope (log-odds per 10 distractors). None when outcomes are all equal or perfectly separated."""
    if len(set(y)) < 2:
        return None
    x, yv = np.array(n) / 10.0, np.array(y)
    nll = lambda b: np.sum(np.logaddexp(0, b[0] + b[1] * x) - yv * (b[0] + b[1] * x))
    res = minimize(nll, np.zeros(2), method="BFGS")
    return None if not res.success or abs(res.x[1]) > 20 else float(res.x[1])


def boot(stat, fam_ids: list[str]) -> dict:
    rng = random.Random(SEED)
    point = stat(fam_ids)
    est = [v for v in (stat(rng.choices(fam_ids, k=len(fam_ids))) for _ in range(N_RESAMPLES)) if v is not None]
    if point is None or len(est) < N_RESAMPLES * 0.9:
        return {"point": point, "lower": None, "upper": None, "note": "not estimable (no variation or separation)"}
    est.sort()
    k = len(est)
    return {"point": point, "lower": est[int(0.025 * k)], "upper": est[int(0.975 * k) - 1], "n_valid_resamples": k}


def main() -> None:
    cs, conds = cases(), conditions()
    fam = [c.id for c in cs]
    store = CassetteStore(Path("cassettes"), mode="replay")
    out: dict = {"temperature": 0.0, "seed": SEED, "n_resamples": N_RESAMPLES, "per_model": {}}
    for m in MODELS:
        p = OpenAICompatProvider(provider_slug="groq", model_id=m, cassette_store=store, temperature=0.0)
        hit: dict[tuple[str, int], dict[str, bool]] = {}
        tokens: dict[tuple[str, int], list[int]] = {}
        for kind, n, surf in conds:
            hit[(kind, n)] = {c.id: grade(c, p.call(c, surf)).verdict == Verdict.correct for c in cs}
            tokens[(kind, n)] = [store.get(p._request_bytes(p._build_request(c, surf))).get("usage", {}).get("prompt_tokens", 0)
                                 for c in cs]
        res: dict = {}
        for kind in KINDS:
            curve = {}
            for n in NS:
                acc = boot(lambda ids, k=kind, n=n: statistics.fmean(hit[(k, n)][i] for i in ids), fam)
                curve[n] = {"accuracy": acc, "mean_prompt_tokens": statistics.fmean(tokens[(kind, n)])}
            slope = boot(lambda ids, k=kind: logistic_slope([n for i in ids for n in NS],
                                                             [float(hit[(k, n)][i]) for i in ids for n in NS]), fam)
            res[kind] = {"curve": curve, "logistic_slope_per_10": slope}
        res["H1_confirmed"] = res["near-duplicate"]["logistic_slope_per_10"]["upper"] is not None and \
            res["near-duplicate"]["logistic_slope_per_10"]["upper"] < 0
        contrast = boot(lambda ids: statistics.fmean(hit[("unrelated", 20)][i] - hit[("near-duplicate", 20)][i] for i in ids), fam)
        mc = mcnemar_test(sum(hit[("unrelated", 20)][i] and not hit[("near-duplicate", 20)][i] for i in fam),
                          sum(hit[("near-duplicate", 20)][i] and not hit[("unrelated", 20)][i] for i in fam))
        res["H2_drop_neardup_vs_unrelated_N20"] = {"contrast": contrast, "mcnemar_p": mc.p_value,
                                                    "confirmed": contrast["lower"] is not None and contrast["lower"] > 0.05}
        res["per_case_hits"] = {f"{k}|{n}": v for (k, n), v in hit.items()}
        out["per_model"][m] = res

    Path("results/exp005_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for m, r in out["per_model"].items():
        print(m)
        for kind in KINDS:
            accs = " ".join(f"N{n}:{r[kind]['curve'][n]['accuracy']['point']:.2f}" for n in NS)
            toks = r[kind]["curve"][50]["mean_prompt_tokens"]
            print(f"  {kind:14} {accs}  slope={r[kind]['logistic_slope_per_10']}  N50 prompt tokens={toks:.0f}")
        print("  H1:", r["H1_confirmed"], " H2:", r["H2_drop_neardup_vs_unrelated_N20"])


if __name__ == "__main__":
    main()
