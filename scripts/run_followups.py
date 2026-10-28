"""Runner for EXP-010, EXP-011 and EXP-012 (docs/experiments/EXP-01{0,1,2}.md).

Same safeguards as run_exp009.py: --dry-run estimate, --max-usd cap, cassettes,
temperature 0, up to 3 passes that re-send only errored trials. Trials are written
to results/exp0NN_<model>.json with their condition labels for the analysis.

  python scripts/run_followups.py --exp 10 --model openai/gpt-oss-120b --dry-run
  python scripts/run_followups.py --exp 11 --model openai/gpt-oss-20b --max-usd 2 --record
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import tiktoken
from dotenv import load_dotenv

from surfacelab.budget import check, estimate
from surfacelab.cases import load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.render import render
from surfacelab.runner import run_experiment
from surfacelab.schema import Surface
from surfacelab.surface import load_fixture_surface
from surfacelab.variants import pad_surface

ND = ["nd_files", "nd_messaging", "nd_documents", "nd_calendar"]
XO = ["files", "mail", "knowledge"]
NS = [0, 2, 5, 10, 20]


def rotations(s: Surface) -> list[Surface]:
    """4 cyclic rotations: each tool once in each position (EXP-010 design)."""
    t = list(s.tools)
    return [Surface(server_name=s.server_name, tools=t[i:] + t[:i]) for i in range(len(t))]


def plan_010():
    cases = load_cases(Path("fixtures/cases/near_dup.jsonl"))
    for s in ND:
        cs = [c for c in cases if c.surface_name == s]
        for cond, name in [("base", s), ("contrast", f"{s}_contrast"), ("negation", f"{s}_negation")]:
            yield {"surface": s, "condition": cond}, cs, rotations(load_fixture_surface(name))


def _remap(gold: str, scheme: str, first: str) -> str:
    server, tool = gold.split("/")
    if scheme == "qualified":
        return gold
    if scheme == "prefix":
        return f"{server}_{tool}"
    return tool if server == first else f"{tool}_2"


def plan_011():
    cases = load_cases(Path("fixtures/cases/cross_overlap.jsonl"))
    for pair in XO:
        q = f"xo_{pair}_qualified"
        cs = [c for c in cases if c.surface_name == q]
        first = load_fixture_surface(q).tools[0].name.split("/")[0]
        for scheme in ["none", "prefix", "qualified"]:
            s = load_fixture_surface(f"xo_{pair}_{scheme}")
            half = len(s.tools) // 2
            orders = [s, Surface(server_name=s.server_name, tools=list(s.tools[half:]) + list(s.tools[:half]))]
            mapped = [c.model_copy(update={"gold": frozenset(_remap(g, scheme, first) for g in c.gold),
                                           "surface_name": s.server_name}) for c in cs]
            yield {"pair": pair, "scheme": scheme}, mapped, orders


def plan_012():
    cases = load_cases(Path("fixtures/cases/near_dup.jsonl"))
    for s in ND:
        base = load_fixture_surface(s)
        cs = [c for c in cases if c.surface_name == s]
        pool = list(load_fixture_surface(s, Path("fixtures/surfaces/distractors")).tools)
        yield {"surface": s, "kind": "none", "n": 0}, cs, [base]
        for n in NS[1:]:
            yield {"surface": s, "kind": "unrelated", "n": n}, cs, [pad_surface(base, n, "unrelated", seed=42)]
            nd = Surface(server_name=base.server_name, tools=list(base.tools) + pool[:n])
            yield {"surface": s, "kind": "near-duplicate", "n": n}, cs, [nd]


PLANS = {10: plan_010, 11: plan_011, 12: plan_012}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", type=int, choices=sorted(PLANS), required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-usd", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    load_dotenv(Path(".env"))

    items = list(PLANS[args.exp]())
    enc = tiktoken.get_encoding("o200k_base")
    tokens = sum((len(enc.encode(json.dumps(render(v)))) + 256) * len(cs) for _, cs, vs in items for v in vs)
    est = estimate(args.model, tokens)
    print(f"EXP-0{args.exp} plan: conditions={len(items)} trials={sum(len(cs) * len(vs) for _, cs, vs in items)}")
    print(f"  {est}")
    if args.dry_run:
        print("(dry-run) No calls made.")
        return
    check(est, args.max_usd)

    store = CassetteStore(Path("cassettes"), mode="record" if args.record else "replay")
    p = OpenAICompatProvider(provider_slug="groq", model_id=args.model, cassette_store=store, temperature=0.0)
    if args.exp == 12:
        p._min_call_interval = 3.0  # padded prompts: keep each org under 8K tokens/minute
    for attempt in range(1, 4):
        rows, n_err = [], 0
        for label, cs, vs in items:
            trials, errors = run_experiment(cs, vs, p.call, workers=args.workers)
            n_err += len(errors)
            rows += [{**label, **asdict(t)} for t in trials]
            print(f"  pass {attempt} {label}: {sum(t.correct for t in trials)}/{len(trials)} correct, "
                  f"{len(errors)} errors", flush=True)
        print(f"pass {attempt}: {n_err} errors", flush=True)
        if n_err == 0:
            break
    out = Path(f"results/exp0{args.exp}_{args.model.split('-')[-1]}.json")
    out.write_text(json.dumps({"model": args.model, "errors": n_err, "trials": rows}, indent=1), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
