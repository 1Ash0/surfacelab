"""EXP-002 analysis: paraphrase flip rate from recorded cassettes (offline, replay only).

Follows docs/experiments/EXP-002.md. Confirmatory set excludes audit-failed families.
Writes results/exp002_analysis.json.
"""

from __future__ import annotations

import json
import random
import re
import statistics
from itertools import combinations
from pathlib import Path

from surfacelab.cases import load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.stats import mcnemar_test
from surfacelab.surface import load_fixture_surface

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
AUDIT_EXCLUDED = {"c007", "c011"}  # failed the manual intent audit (fixtures/cases/paraphrase_audit.csv)
N_RESAMPLES, SEED = 10_000, 42


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def flip_rate(answers: list[str | None]) -> float:
    pairs = list(combinations(answers, 2))
    return sum(a != b for a, b in pairs) / len(pairs)


def boot_mean(values: list[float]) -> dict:
    rng = random.Random(SEED)
    est = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(N_RESAMPLES))
    return dict(point=statistics.fmean(values), lower=est[int(0.025 * N_RESAMPLES)],
                upper=est[int(0.975 * N_RESAMPLES) - 1])


def verdict(ci: dict) -> str:
    return "fragile" if ci["lower"] > 0.10 else "robust" if ci["upper"] < 0.05 else "inconclusive"


def analyse(fams: dict[str, list[dict]], overlap: dict[str, float]) -> dict:
    flips = {f: flip_rate([t["emitted"] for t in ts]) for f, ts in fams.items()}
    ci = boot_mean(list(flips.values()))
    pairs = [(o["correct"], p["correct"]) for ts in fams.values()
             for o in ts if o["is_original"] for p in ts if not p["is_original"]]
    mc = mcnemar_test(sum(a and not b for a, b in pairs), sum(b and not a for a, b in pairs))
    scored = {f: v for f, v in flips.items() if f in overlap}
    med = statistics.median(overlap[f] for f in scored)
    hi = [v for f, v in scored.items() if overlap[f] > med]
    lo = [v for f, v in scored.items() if overlap[f] <= med]
    return {
        "n_families": len(fams),
        "accuracy": sum(t["correct"] for ts in fams.values() for t in ts) / sum(len(ts) for ts in fams.values()),
        "mean_flip_rate": ci, "verdict": verdict(ci),
        "H1_families_with_any_flip": sum(v > 0 for v in flips.values()),
        "H1_supported": sum(v > 0 for v in flips.values()) >= len(flips) / 2,
        "H2_flip_above_vs_at_or_below_median_overlap": {
            "above": statistics.fmean(hi) if hi else None, "at_or_below": statistics.fmean(lo) if lo else None,
            "n_above": len(hi), "n_at_or_below": len(lo), "note": "abstain families have no gold tool and are excluded"},
        "mcnemar_original_vs_paraphrase_correct": {
            "original_only": mc.n_ab, "paraphrase_only": mc.n_ba, "p_value": mc.p_value,
            "caveat": "pairs within a family are not independent"},
        "flip_rate_per_family": flips,
    }


def main() -> None:
    surface = load_fixture_surface("goodserver")
    desc = {t.name: t.description for t in surface.tools}
    cases = load_cases(Path("fixtures/cases/core_paraphrased.jsonl"))
    overlap = {}
    for c in cases:
        if "_p" not in c.id and c.gold:
            req, d = tokens(c.request), tokens(desc[next(iter(c.gold))])
            overlap[c.id] = len(req & d) / len(req | d)

    store = CassetteStore(Path("cassettes"), mode="replay")
    out: dict = {"temperature": 0.0, "n_resamples": N_RESAMPLES, "seed": SEED,
                 "audit_excluded": sorted(AUDIT_EXCLUDED), "per_model": {}}
    for m in MODELS:
        p = OpenAICompatProvider(provider_slug="groq", model_id=m, cassette_store=store, temperature=0.0)
        fams: dict[str, list[dict]] = {}
        for c in cases:
            emitted = p.call(c, surface)
            correct = (emitted is None) if not c.gold else (emitted in c.gold)
            fams.setdefault(c.id.split("_p")[0], []).append(
                {"id": c.id, "emitted": emitted, "correct": correct, "is_original": "_p" not in c.id})
        confirm = {f: ts for f, ts in fams.items() if f not in AUDIT_EXCLUDED}
        out["per_model"][m] = {"confirmatory": analyse(confirm, overlap), "exploratory_all_families": analyse(fams, overlap),
                               "answers": {f: [t["emitted"] for t in ts] for f, ts in fams.items()}}

    Path("results/exp002_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for m, r in out["per_model"].items():
        c = r["confirmatory"]
        print(m, "confirmatory:", {k: v for k, v in c.items() if k != "flip_rate_per_family"})
        print("  families with flips:", {f: round(v, 2) for f, v in c["flip_rate_per_family"].items() if v})
        print("  all-15 mean flip:", r["exploratory_all_families"]["mean_flip_rate"])


if __name__ == "__main__":
    main()
