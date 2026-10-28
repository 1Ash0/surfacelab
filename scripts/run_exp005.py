"""EXP-005 runner: goodserver padded with N distractors of each kind (docs/experiments/EXP-005.md).

Surfaces are built at run time with pad_surface(..., seed=42), so the fixture-based
`surfacelab run` cannot load them. Same safeguards: --dry-run estimate, --max-usd cap,
cassette record/replay, temperature 0. Up to 3 passes re-send trials that errored.

  python scripts/run_exp005.py --model openai/gpt-oss-20b --dry-run
  python scripts/run_exp005.py --model openai/gpt-oss-20b --max-usd 5 --record
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import tiktoken
from dotenv import load_dotenv

from surfacelab.budget import check, estimate
from surfacelab.cases import CaseKind, load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.render import render
from surfacelab.runner import run_experiment
from surfacelab.schema import Surface
from surfacelab.surface import load_fixture_surface
from surfacelab.variants import pad_surface

NS = [0, 5, 10, 20, 50]
KINDS = ["unrelated", "same-domain", "near-duplicate"]
SEED = 42


def conditions() -> list[tuple[str, int, Surface]]:
    base = load_fixture_surface("goodserver")
    return [(k, n, pad_surface(base, n, k, seed=SEED)) for k in KINDS for n in NS]


def cases():
    return [c for c in load_cases(Path("fixtures/cases/core.jsonl")) if c.kind == CaseKind.positive]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-usd", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    load_dotenv(Path(".env"))

    cs, conds = cases(), conditions()
    enc = tiktoken.get_encoding("o200k_base")
    tokens = sum((len(enc.encode(json.dumps(render(s)))) + 256) * len(cs) for _, _, s in conds)
    est = estimate(args.model, tokens)
    print(f"EXP-005 plan: cases={len(cs)} conditions={len(conds)} trials={len(cs) * len(conds)}")
    print(f"  {est}")
    if args.dry_run:
        print("(dry-run) No calls made.")
        return
    check(est, args.max_usd)

    store = CassetteStore(Path("cassettes"), mode="record" if args.record else "replay")
    p = OpenAICompatProvider(provider_slug="groq", model_id=args.model, cassette_store=store, temperature=0.0)
    p._min_call_interval = 3.0  # larger prompts: keep each org under 8K tokens/minute
    for attempt in range(1, 4):
        n_err, n_ok = 0, 0
        for kind, n, surface in conds:
            trials, errors = run_experiment(cs, [surface], p.call, workers=args.workers)
            n_err += len(errors)
            n_ok += sum(t.correct for t in trials)
            for e in errors:
                print(f"  {kind} N={n} {e.case_id}: {e.message[:120]}")
            print(f"  pass {attempt} {kind:14} N={n:2}: {sum(t.correct for t in trials)}/{len(trials)} correct, "
                  f"{len(errors)} errors", flush=True)
        print(f"pass {attempt}: {n_ok} correct, {n_err} errors")
        if n_err == 0:
            break


if __name__ == "__main__":
    main()
