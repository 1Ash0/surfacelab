"""EXP-014 analysis: three replications on qwen/qwen3.8-27b (docs/experiments/EXP-014.md).
Replay only; reuses the original statistics. Writes results/exp014_analysis.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["SURFACELAB_MODELS"] = "qwen/qwen3.8-27b"
import analyze_exp001 as e1  # noqa: E402
import analyze_exp009 as e9  # noqa: E402
import analyze_followups as fu  # noqa: E402

Q = "qwen/qwen3.8-27b"


def verdict(hit: bool, miss: bool) -> str:
    return "replicated" if hit else "not_replicated" if miss else "inconclusive"


def main() -> None:
    e9.MODELS[:] = [Q]  # analyze_exp009 imported MODELS by value
    sib = e1.collect(surfaces=[e1.SURFACES[1]], temperature=0.0)
    r1 = e1.boot(e1.gap, [e1.families(sib, model=Q)])
    nd = e9.collect()
    fam = e1.families(nd, model=Q)
    r2 = e1.boot(lambda f: e1.acc([t for x in f.values() for t in x]), [fam])
    x11 = fu.exp011()["models"]["27b"]["none"]
    out = {
        "model": Q,
        "R1_siblings_gap": {**r1, "accuracy": e1.acc(sib),
                            "verdict": verdict(r1["lower"] > 0, r1["upper"] < 0)},
        "R2_nd_accuracy": {**r2, "trials": len(nd), "refusals": sum(r["emitted"] is None for r in nd),
                           "position_gap": e1.boot(e1.gap, [fam]),
                           "verdict": verdict(r2["lower"] >= 0.95, r2["upper"] < 0.95)},
        "R3_collision_none": {**x11, "verdict": verdict(x11["wilson"][1] < 0.10, x11["wilson"][0] > 0.10)},
    }
    Path("results/exp014_analysis.json").write_text(json.dumps(out, indent=1, default=list), encoding="utf-8")
    print(json.dumps({k: v.get("verdict") if isinstance(v, dict) else v for k, v in out.items()}, indent=1))
    print(json.dumps({k: {kk: out[k][kk] for kk in ("point", "lower", "upper") if kk in out[k]} for k in ["R1_siblings_gap", "R2_nd_accuracy"]}))
    print(out["R2_nd_accuracy"]["position_gap"], out["R3_collision_none"]["counts"], out["R3_collision_none"]["wilson"])


if __name__ == "__main__":
    main()
