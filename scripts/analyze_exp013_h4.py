"""EXP-013 H4 (exploratory): on unique-case errors that called a real, wrong tool, how similar is
that tool to the gold tool compared with the other wrong tools? Percentile (share of non-gold tools less similar to gold) of the emitted tool's
similarity to gold among all non-gold tools in the loadout (1.0 = the most similar). Both EXP-004
embedding models. Writes results/exp013_h4.json."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from scipy.stats import wilcoxon

from analyze_exp004 import EMBEDDERS
from surfacelab.cases import load_cases
from surfacelab.embed import EmbedStore
from surfacelab.schema import Surface
from surfacelab.similarity import similarity_matrix


def main() -> None:
    load_dotenv(Path(".env"))
    cases = {c.id: c for c in load_cases(Path("fixtures/cases/real_loadouts.jsonl"))}
    out: dict = {}
    for prov, model in EMBEDDERS:
        store = EmbedStore(prov, model, Path("cassettes/embed"))
        sims = {}
        for name in ["browser", "web", "workspace", "docs"]:
            s = Surface.model_validate_json(Path(f"fixtures/surfaces/real_{name}.json").read_text())
            m = similarity_matrix(store.embed_surface(s))
            idx = {t.name: i for i, t in enumerate(s.tools)}
            sims[name] = (idx, m)
        per_case: dict[str, list[float]] = {}
        for mid in ["20b", "120b", "27b"]:
            for r in json.loads(Path(f"results/exp013_{mid}.json").read_text())["trials"]:
                c = cases[r["case_id"]]
                idx, m = sims[r["loadout"]]
                if r["correct"] or r["emitted"] not in idx:
                    continue
                score = lambda n: max(m[idx[n]][idx[g]] for g in c.gold)
                others = [n for n in idx if n not in c.gold]
                e = score(r["emitted"])
                per_case.setdefault(c.id, []).append(sum(score(n) < e for n in others) / len(others))
        # One value per case family: repeated trials of a case are not independent (CLAUDE.md rule 4).
        pct = [mean(v) for v in per_case.values()]
        stat = wilcoxon([p - 0.5 for p in pct], alternative="greater") if pct else None
        out[model] = {"n_error_trials": sum(len(v) for v in per_case.values()), "n_families": len(pct), "mean_percentile": mean(pct) if pct else None,
                      "share_in_top_quartile": sum(p >= 0.75 for p in pct) / len(pct) if pct else None,
                      "wilcoxon_p_greater_than_0.5": float(stat.pvalue) if stat else None}
        print(model, out[model])
    Path("results/exp013_h4.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
