"""EXP-003 analysis: per-edit paired accuracy delta vs base (offline, replay only).

Follows docs/experiments/EXP-003.md. Primary set is the held-out split c011-c015;
all 15 families are reported as exploratory. Writes results/exp003_analysis.json.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import tiktoken

from surfacelab.cases import load_cases
from surfacelab.grading import Verdict, grade
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.stats import holm_correction, mcnemar_test
from surfacelab.surface import load_fixture_surface

MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
EDITS = ["add_usage", "add_negation", "prepend_summary", "trim", "set_desc_vague"]
CONFIRMATORY = {"add_usage": "H1", "set_desc_vague": "H2"}
EVAL_SPLIT = {"c011", "c012", "c013", "c014", "c015"}
N_RESAMPLES, SEED = 10_000, 42
ENC = tiktoken.get_encoding("o200k_base")  # gpt-oss tokenizer family


def desc_tokens(surface_name: str) -> int:
    return sum(len(ENC.encode(t.description)) for t in load_fixture_surface(surface_name).tools)


def boot_mean(values: list[float]) -> dict:
    rng = random.Random(SEED)
    est = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(N_RESAMPLES))
    return dict(point=statistics.fmean(values), lower=est[int(0.025 * N_RESAMPLES)],
                upper=est[int(0.975 * N_RESAMPLES) - 1])


def verdict(ci: dict, token_increase: float) -> str:
    if ci["lower"] > 0.05:
        return "helps"
    if ci["upper"] < -0.05:
        return "regresses"
    if ci["lower"] <= 0 <= ci["upper"] and token_increase > 0.20:
        return "costs"
    return "inconclusive"


def compare(base: dict[str, bool], edit: dict[str, bool], ids: set[str], tok_inc: float) -> dict:
    deltas = [float(edit[c]) - float(base[c]) for c in sorted(ids)]
    mc = mcnemar_test(sum(edit[c] and not base[c] for c in ids), sum(base[c] and not edit[c] for c in ids))
    ci = boot_mean(deltas)
    return {"n_families": len(ids), "base_accuracy": statistics.fmean(base[c] for c in ids),
            "edit_accuracy": statistics.fmean(edit[c] for c in ids), "delta": ci,
            "mcnemar": {"edit_only_correct": mc.n_ab, "base_only_correct": mc.n_ba, "p_value": mc.p_value},
            "verdict": verdict(ci, tok_inc)}


def main() -> None:
    cases = load_cases(Path("fixtures/cases/core.jsonl"))
    store = CassetteStore(Path("cassettes"), mode="replay")
    base_tok = desc_tokens("goodserver")
    out: dict = {"temperature": 0.0, "n_resamples": N_RESAMPLES, "seed": SEED, "eval_split": sorted(EVAL_SPLIT),
                 "description_tokens": {"goodserver": base_tok}, "per_model": {}}
    for m in MODELS:
        p = OpenAICompatProvider(provider_slug="groq", model_id=m, cassette_store=store, temperature=0.0)
        correct: dict[str, dict[str, bool]] = {}
        for s in ["goodserver"] + [f"goodserver_{e}" for e in EDITS]:
            surf = load_fixture_surface(s)
            correct[s] = {c.id: grade(c, p.call(c, surf)).verdict == Verdict.correct for c in cases}
        res: dict = {}
        for e in EDITS:
            s = f"goodserver_{e}"
            tok = desc_tokens(s)
            out["description_tokens"][s] = tok
            inc = (tok - base_tok) / base_tok
            res[e] = {"label": CONFIRMATORY.get(e, "exploratory"), "description_token_increase": inc,
                      "primary_eval_split": compare(correct["goodserver"], correct[s], EVAL_SPLIT, inc),
                      "all_families_exploratory": compare(correct["goodserver"], correct[s], {c.id for c in cases}, inc)}
        confirm = [e for e in EDITS if e in CONFIRMATORY]
        rejected = holm_correction([res[e]["primary_eval_split"]["mcnemar"]["p_value"] for e in confirm])
        for e, r in zip(confirm, rejected):
            res[e]["holm_rejects_null"] = r
        res["per_case_correct"] = correct
        out["per_model"][m] = res

    Path("results/exp003_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for m, r in out["per_model"].items():
        print(m)
        for e in EDITS:
            pe, al = r[e]["primary_eval_split"], r[e]["all_families_exploratory"]
            print(f"  {e:16} {r[e]['label']:11} tok+{r[e]['description_token_increase']:+.0%}  "
                  f"eval: {pe['base_accuracy']:.2f}->{pe['edit_accuracy']:.2f} {pe['verdict']:12} "
                  f"all15: {al['base_accuracy']:.2f}->{al['edit_accuracy']:.2f} delta={al['delta']['point']:+.3f} "
                  f"[{al['delta']['lower']:+.2f},{al['delta']['upper']:+.2f}] p={al['mcnemar']['p_value']:.3f}")


if __name__ == "__main__":
    main()
