"""EXP-009 runner: each near-duplicate surface with its own 8 cases, all 24 orderings.

`surfacelab run` takes one surface per call and would run all 32 cases on it, so this
pairs cases with their surface. Same safeguards: --dry-run estimate, --max-usd cap,
cassettes, temperature 0, and up to 3 passes that re-send only errored trials.

  python scripts/run_exp009.py --model openai/gpt-oss-20b --dry-run
  python scripts/run_exp009.py --model openai/gpt-oss-20b --max-usd 5 --record
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import tiktoken
from dotenv import load_dotenv

from surfacelab.budget import check, estimate
from surfacelab.cases import load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.render import render
from surfacelab.runner import run_experiment
from surfacelab.surface import load_fixture_surface
from surfacelab.variants import balanced_permutations

SURFACES = ["nd_files", "nd_messaging", "nd_documents", "nd_calendar"]
K = 24


def plan():
    cases = load_cases(Path("fixtures/cases/near_dup.jsonl"))
    for s in SURFACES:
        yield s, [c for c in cases if c.surface_name == s], balanced_permutations(load_fixture_surface(s), K)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-usd", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    load_dotenv(Path(".env"))

    enc = tiktoken.get_encoding("o200k_base")
    items = list(plan())
    tokens = sum((len(enc.encode(json.dumps(render(v[0])))) + 256) * len(cs) * len(v) for _, cs, v in items)
    est = estimate(args.model, tokens)
    n = sum(len(cs) * len(v) for _, cs, v in items)
    print(f"EXP-009 plan: surfaces={len(items)} cases={sum(len(cs) for _, cs, _ in items)} orderings={K} trials={n}")
    print(f"  {est}")
    if args.dry_run:
        print("(dry-run) No calls made.")
        return
    check(est, args.max_usd)

    store = CassetteStore(Path("cassettes"), mode="record" if args.record else "replay")
    p = OpenAICompatProvider(provider_slug="groq", model_id=args.model, cassette_store=store, temperature=0.0)
    for attempt in range(1, 4):
        n_err = 0
        for s, cs, variants in items:
            trials, errors = run_experiment(cs, variants, p.call, workers=args.workers)
            n_err += len(errors)
            kinds: dict[str, int] = {}
            for e in errors:
                key = e.message.split(" - ")[0][:60]
                kinds[key] = kinds.get(key, 0) + 1
            print(f"  pass {attempt} {s:13}: {sum(t.correct for t in trials)}/{len(trials)} correct, "
                  f"{len(errors)} errors {kinds or ''}", flush=True)
        print(f"pass {attempt}: {n_err} errors", flush=True)
        if n_err == 0:
            break


if __name__ == "__main__":
    main()
