"""EXP-009 analysis (docs/experiments/EXP-009.md). Replay only; reuses the EXP-001 thirds gap
and clustered bootstrap. Writes results/exp009_analysis.json."""

from __future__ import annotations

import json
from pathlib import Path

from analyze_exp001 import MODELS, acc, boot, families, gap
from run_exp009 import plan
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider


def collect() -> list[dict]:
    store = CassetteStore(Path("cassettes"), mode="replay")
    rows = []
    for model in MODELS:
        prov = OpenAICompatProvider(provider_slug="groq", model_id=model, cassette_store=store, temperature=0.0)
        for s, cases, variants in plan():
            for case in cases:
                gold = next(iter(case.gold))
                for vi, v in enumerate(variants):
                    names = [t.name for t in v.tools]
                    emitted = prov.call(case, v)
                    rows.append(dict(model=model, surface=s, case=case.id, variant=vi, pos=names.index(gold),
                                     n=len(names), emitted=emitted, correct=emitted in case.gold))
    return rows


def verdict(ci: dict) -> str:
    if ci["lower"] > 0:
        return "position_effect_confirmed"
    if ci["upper"] < 0.05:
        return "position_effect_absent"
    return "inconclusive"


def main() -> None:
    rows = collect()
    out = {"models": {}}
    for m in MODELS:
        fams = families(rows, model=m)
        ci = boot(gap, [fams])
        per_surface = {s: {"accuracy": acc([r for r in rows if r["model"] == m and r["surface"] == s]),
                           "gap": gap(families(rows, model=m, surface=s))}
                       for s in sorted({r["surface"] for r in rows})}
        ts = [r for r in rows if r["model"] == m]
        out["models"][m] = dict(trials=len(ts), accuracy=acc(ts), refusals=sum(r["emitted"] is None for r in ts),
                                by_position={p: acc([r for r in ts if r["pos"] == p]) for p in range(4)},
                                gap=ci, verdict=verdict(ci), per_surface_exploratory=per_surface,
                                wrong=[(r["case"], r["variant"], r["emitted"]) for r in ts if not r["correct"]])
    Path("results/exp009_analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
