"""Does temperature=0 make Groq's gpt-oss deterministic? Repeats identical requests live.

Bypasses the cassette store on purpose: identical requests share a cassette key,
so replay would hide any run-to-run variation. Writes results/determinism_probe.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from surfacelab.cases import load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.surface import load_fixture_surface
from surfacelab.variants import balanced_permutations

REPEATS, CASES, ORDERINGS = 5, 4, 2


def live(p: OpenAICompatProvider, request: dict) -> dict:
    import openai
    for attempt in range(3):
        try:
            return p._make_live_call(request)
        except (openai.APIConnectionError, openai.APITimeoutError):
            if attempt == 2:
                raise
    raise RuntimeError("unreachable")


def emitted(raw: dict) -> str | None:
    calls = (raw.get("choices") or [{}])[0].get("message", {}).get("tool_calls") or []
    return calls[0]["function"]["name"] if calls else None


def main() -> None:
    load_dotenv(Path(".env"))
    temperature = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    cases = load_cases(Path("fixtures/cases/siblings.jsonl"))[:CASES]
    variants = balanced_permutations(load_fixture_surface("siblings"), 24)[:ORDERINGS]
    store = CassetteStore(Path("cassettes"), mode="replay")  # unused: live calls only
    out: dict = {"temperature": temperature, "repeats": REPEATS, "models": {}}
    for model in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
        p = OpenAICompatProvider(provider_slug="groq", model_id=model, cassette_store=store, temperature=temperature)
        groups = []
        for c in cases:
            for vi, v in enumerate(variants):
                answers = [emitted(live(p, p._build_request(c, v))) for _ in range(REPEATS)]
                groups.append({"case": c.id, "variant": vi, "answers": answers})
                print(model, c.id, vi, answers, flush=True)
        stable = sum(len(set(g["answers"])) == 1 for g in groups)
        out["models"][model] = {"groups": groups, "n_groups": len(groups), "n_fully_stable": stable}
    Path("results/determinism_probe.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for m, r in out["models"].items():
        print(f"{m}: {r['n_fully_stable']}/{r['n_groups']} request groups gave the same answer all {REPEATS} times")


if __name__ == "__main__":
    main()
