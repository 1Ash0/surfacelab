"""Power simulation: clustered CI half-width vs number of case families.

Estimates how many case families are needed so the clustered bootstrap 95% CI
half-width on accuracy falls below a target delta (e.g. 0.05 = ±5 pp).

Usage:
    uv run python scripts/power_sim.py          # defaults
    uv run python scripts/power_sim.py --p0 0.7 --delta 0.05 --k 4 --trials 3

Parameters
----------
p0      Baseline accuracy (fraction of cases correct).
delta   Target CI half-width in percentage points (e.g. 0.05 = ±5 pp).
k       Number of surface variants per case family.
trials  Number of independent trials per (case, variant).
n_sim   Bootstrap resamples per n_families evaluation.

Outputs: a table of (n_families, mean_halfwidth, p80_halfwidth) for
n_families in {5, 10, 15, 20, 30, 40, 50, 75, 100}.
Also writes results/power_sim.json.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from surfacelab.stats import wilson_interval

RESULTS = Path(__file__).parent.parent / "results"
RESULTS.mkdir(exist_ok=True)


def _simulate_halfwidth(
    n_families: int,
    p0: float,
    k: int,
    trials: int,
    n_sim: int,
    rng: random.Random,
) -> float:
    """Return mean bootstrap CI half-width over n_sim simulations."""
    halfwidths: list[float] = []

    for _ in range(n_sim):
        # Simulate n_families case families, each with k*trials binary outcomes.
        # Clustered bootstrap: resample families with replacement.
        family_hits = [
            sum(1 for _ in range(k * trials) if rng.random() < p0)
            for _ in range(n_families)
        ]
        family_counts = [k * trials] * n_families

        # Bootstrap over families (10,000 resamples would be ideal;
        # use 500 here for speed since we're simulating many n values).
        boot_accs: list[float] = []
        n_boot = 500
        for _ in range(n_boot):
            idxs = [rng.randint(0, n_families - 1) for _ in range(n_families)]
            hits = sum(family_hits[i] for i in idxs)
            total = sum(family_counts[i] for i in idxs)
            boot_accs.append(hits / total if total > 0 else 0.0)

        boot_accs.sort()
        lo = boot_accs[int(0.025 * n_boot)]
        hi = boot_accs[int(0.975 * n_boot)]
        halfwidths.append((hi - lo) / 2)

    halfwidths.sort()
    mean_hw = sum(halfwidths) / len(halfwidths)
    return mean_hw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--p0", type=float, default=0.70, help="Baseline accuracy")
    parser.add_argument("--delta", type=float, default=0.08, help="Target half-width")
    parser.add_argument("--k", type=int, default=4, help="Variants per family")
    parser.add_argument("--trials", type=int, default=1, help="Trials per variant")
    parser.add_argument("--n-sim", type=int, default=200, help="Simulations per n")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    n_values = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]

    print(f"Power simulation  p0={args.p0}  target_halfwidth≤{args.delta}  k={args.k}  trials={args.trials}")
    print(f"{'n_families':>12}  {'mean_halfwidth':>16}  {'meets_target':>12}")
    print("-" * 46)

    rows = []
    for n in n_values:
        hw = _simulate_halfwidth(n, args.p0, args.k, args.trials, args.n_sim, rng)
        meets = hw <= args.delta
        print(f"{n:>12}  {hw:>16.4f}  {'YES' if meets else 'no':>12}")
        rows.append({"n_families": n, "mean_halfwidth": round(hw, 4), "meets_target": meets})

    # Wilson for the full n (simple, not clustered) for comparison
    total = n_values[-1] * args.k * args.trials
    hits = int(total * args.p0)
    lo, hi = wilson_interval(hits, total)
    wilson_hw = (hi - lo) / 2
    print(f"\nWilson (non-clustered, n={n_values[-1]} families): half-width = {wilson_hw:.4f}")

    out = RESULTS / "power_sim.json"
    out.write_text(json.dumps({
        "params": vars(args),
        "rows": rows,
        "wilson_comparison": {"n_families": n_values[-1], "halfwidth": round(wilson_hw, 4)},
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
