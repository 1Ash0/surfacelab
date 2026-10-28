"""Write the blind gold-validation sheet for EXP-013: one row per (case, candidate tool) with the
tool's full description, so the validator judges real tools, not names they imagine.
Loadouts of 10 tools or fewer show every tool; larger ones show 8: the gold tools, then tools
chosen by word overlap, then random ones, shuffled with seed 42 so position does not reveal gold."""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

from surfacelab.cases import load_cases
from surfacelab.schema import Surface

STOP = {"the", "and", "for", "browser", "file", "files", "git", "page"}


def words(s: str) -> set[str]:
    return {w for w in re.split(r"[^a-z]+", s.lower()) if len(w) > 2} - STOP


def main() -> None:
    cases = load_cases(Path("fixtures/cases/real_loadouts.jsonl"))
    rng, rows, shared = random.Random(42), [], 0
    for c in cases:
        s = Surface.model_validate_json(Path(f"fixtures/surfaces/{c.surface_name}.json").read_text())
        own = json.loads(Path(f"fixtures/surfaces/{c.surface_name}.servers.json").read_text())
        desc = {t.name: " ".join(t.description.split()) for t in s.tools}
        assert c.gold <= set(desc), c.id
        assert not [n for n in desc if n.lower() in c.request.lower()], f"{c.id}: tool name in request"
        if c.note.startswith("[shared]"):
            shared += 1
            assert len({own[g] for g in c.gold}) >= 2, f"{c.id}: shared case needs two servers"
        if len(desc) <= 10:
            cand = list(desc)
        else:
            key = words(" ".join(c.gold).replace("_", " ").replace("-", " ")) | words(c.request)
            sim = [n for n in desc if n not in c.gold and words(n.replace("_", " ") + " " + desc[n][:120]) & key]
            rng.shuffle(sim)
            rest = [n for n in desc if n not in c.gold and n not in sim]
            rng.shuffle(rest)
            cand = list(c.gold) + (sim + rest)[: 8 - len(c.gold)]  # always 8, so the count hides nothing
        rng.shuffle(cand)
        rows += [[c.id, c.request, n, own[n], desc[n], ""] for n in cand]
    with open("fixtures/cases/gold_validation_exp013.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "request", "tool", "server", "tool_description", "correct (y/n)"])
        w.writerows(rows)
    print(f"{len(cases)} cases, {shared} shared, {len(rows)} rows")


if __name__ == "__main__":
    main()
