"""EXP-002 step 1-4: generate, filter, sample and pick an audit set of paraphrases.

Generation calls are cassetted under cassettes/paraphrase/ (EXP-002 plan), so
re-running is free and deterministic. Outputs:
  fixtures/cases/core_paraphrased.jsonl   originals + up to 5 paraphrases per family
  fixtures/cases/paraphrase_audit.csv     20% random sample for manual intent check
  results/paraphrase_generation.json      per-family pass counts and rejection reasons
"""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

from dotenv import load_dotenv

from surfacelab.cases import load_cases
from surfacelab.providers.cassette import CassetteStore
from surfacelab.providers.openai_compat import OpenAICompatProvider
from surfacelab.variants import paraphrase_valid

MODEL, N_CANDIDATES, N_KEEP, AUDIT_FRACTION, SEED = "openai/gpt-oss-120b", 10, 5, 0.2, 42

PROMPT = """Rewrite the user request below in {n} different ways.
Rules:
- Keep the exact same intent; a helpful assistant must do the same thing for every version.
- Keep every name, place, number, date, file path and quoted text exactly as written.
- Vary wording and sentence structure; do not just swap one word.
- Do not mention tools, functions or APIs.
Return only a JSON array of {n} strings, nothing else.

Request: {request}"""


def main() -> None:
    load_dotenv(Path(".env"))
    store = CassetteStore(Path("cassettes/paraphrase"), mode="record")
    p = OpenAICompatProvider(provider_slug="groq", model_id=MODEL, cassette_store=store)
    rng = random.Random(SEED)
    out_cases, report, accepted = [], {}, []

    for case in load_cases(Path("fixtures/cases/core.jsonl")):
        request = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT.format(n=N_CANDIDATES, request=case.request)}]}
        raw = store.call(json.dumps(request, sort_keys=True).encode(), lambda _b: p._make_live_call(request))
        text = (raw["choices"][0]["message"].get("content") or "").strip()
        match = re.search(r"\[.*\]", text, re.S)
        candidates = [c.strip() for c in json.loads(match.group(0))] if match else []

        passed, rejected = [], []
        for c in dict.fromkeys(candidates):  # drop exact duplicates, keep order
            ok, reason = paraphrase_valid(case.request, c)
            (passed if ok else rejected).append(c if ok else {"candidate": c, "reason": reason})
        kept = rng.sample(passed, min(N_KEEP, len(passed)))

        out_cases.append(case.model_dump(mode="json"))
        for i, text_i in enumerate(kept, 1):
            out_cases.append({**case.model_dump(mode="json"), "id": f"{case.id}_p{i}", "request": text_i,
                              "note": f"paraphrase {i} of {case.id}"})
            accepted.append((case.id, f"{case.id}_p{i}", case.request, text_i))
        report[case.id] = {"n_candidates": len(candidates), "n_passed": len(passed), "n_kept": len(kept),
                           "short_of_target": len(kept) < N_KEEP, "rejected": rejected}
        print(f"{case.id}: {len(candidates)} candidates, {len(passed)} passed, {len(kept)} kept")

    with Path("fixtures/cases/core_paraphrased.jsonl").open("w", encoding="utf-8") as f:
        for c in out_cases:
            c["gold"] = sorted(c["gold"])
            f.write(json.dumps(c) + "\n")

    audit = rng.sample(accepted, max(1, round(AUDIT_FRACTION * len(accepted))))
    with Path("fixtures/cases/paraphrase_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["family", "paraphrase_id", "original", "paraphrase", "intent_preserved (yes/no)", "comment"])
        for row in sorted(audit):
            w.writerow([*row, "", ""])

    Path("results/paraphrase_generation.json").write_text(json.dumps(
        {"model": MODEL, "n_candidates": N_CANDIDATES, "n_keep": N_KEEP, "seed": SEED,
         "n_accepted": len(accepted), "n_audit": len(audit), "families": report}, indent=2), encoding="utf-8")
    print(f"accepted {len(accepted)} paraphrases; audit sheet has {len(audit)} rows")


if __name__ == "__main__":
    main()
