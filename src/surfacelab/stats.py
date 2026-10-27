"""Statistical tests for tool-choice robustness experiments.

Wilson interval, clustered bootstrap, McNemar's exact test, Holm correction,
Cochran's Q. All functions are pure (no randomness except bootstrap, which
accepts a seed for reproducibility). No third-party stats library required.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Wilson score interval
# ---------------------------------------------------------------------------

_Z95 = 1.959964  # z_{0.975}


def wilson_interval(
    successes: int,
    trials: int,
    z: float = _Z95,
) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Returns (lower, upper) in [0, 1]. More accurate than the Wald (naive)
    interval near 0 and 1. With z=1.96 this is a 95% CI.
    """
    if trials == 0:
        return (0.0, 1.0)
    p_hat = successes / trials
    z2 = z * z
    denom = trials + z2
    center = (successes + z2 / 2) / denom
    margin = z * math.sqrt(trials * p_hat * (1 - p_hat) + z2 / 4) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


# ---------------------------------------------------------------------------
# Clustered bootstrap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BootstrapCI:
    lower: float
    upper: float
    point: float  # empirical accuracy over the observed families


def clustered_bootstrap(
    families: list[list[bool]],
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> BootstrapCI:
    """Bootstrap CI by resampling case families, not individual trials.

    Each replicate draws len(families) families with replacement and computes
    accuracy = (#correct trials) / (#total trials) across the drawn families.
    This preserves within-family correlation that naively resampling trials
    would ignore — see _trial_bootstrap_BROKEN for the instructive contrast.

    families[i] = list of per-trial boolean outcomes for family i.
    """
    rng = random.Random(seed)
    n = len(families)
    if n == 0:
        return BootstrapCI(lower=0.0, upper=1.0, point=0.0)

    flat = [t for f in families for t in f]
    point = sum(flat) / len(flat) if flat else 0.0

    estimates: list[float] = []
    for _ in range(n_resamples):
        sample = rng.choices(families, k=n)
        all_trials = [t for f in sample for t in f]
        if all_trials:
            estimates.append(sum(all_trials) / len(all_trials))

    estimates.sort()
    lo_idx = max(0, int((1 - ci) / 2 * len(estimates)))
    hi_idx = min(len(estimates) - 1, int((1 + ci) / 2 * len(estimates)) - 1)
    return BootstrapCI(lower=estimates[lo_idx], upper=estimates[hi_idx], point=point)


def _trial_bootstrap_BROKEN(  # pyright: ignore[reportUnusedFunction]
    families: list[list[bool]],
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> BootstrapCI:
    """INTENTIONALLY WRONG: resamples individual trials, ignoring family structure.

    Included for the U3 break-it exercise. Produces intervals that are too
    narrow when within-family outcomes are correlated. Do not use in analysis.
    """
    rng = random.Random(seed)
    flat = [t for f in families for t in f]
    if not flat:
        return BootstrapCI(lower=0.0, upper=1.0, point=0.0)

    point = sum(flat) / len(flat)
    estimates: list[float] = []
    for _ in range(n_resamples):
        sample = rng.choices(flat, k=len(flat))
        estimates.append(sum(sample) / len(sample))

    estimates.sort()
    lo_idx = max(0, int((1 - ci) / 2 * len(estimates)))
    hi_idx = min(len(estimates) - 1, int((1 + ci) / 2 * len(estimates)) - 1)
    return BootstrapCI(lower=estimates[lo_idx], upper=estimates[hi_idx], point=point)


# ---------------------------------------------------------------------------
# McNemar's exact test
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class McNemarResult:
    n_ab: int            # A correct, B wrong
    n_ba: int            # B correct, A wrong
    n_discordant: int
    chi2: float          # chi-squared approximation (for reporting only)
    p_value: float       # exact two-tailed p-value via binomial


def _binom_pmf(k: int, n: int) -> float:
    """P(X = k) where X ~ Bin(n, 0.5). Exact."""
    return math.comb(n, k) * (0.5 ** n)


def _binom_cdf_half(k: int, n: int) -> float:
    """P(X <= k) where X ~ Bin(n, 0.5). Exact."""
    return sum(_binom_pmf(i, n) for i in range(k + 1))


def mcnemar_test(n_ab: int, n_ba: int) -> McNemarResult:
    """McNemar's exact test for paired binary data.

    n_ab: cases where system A was correct and B was wrong.
    n_ba: cases where system B was correct and A was wrong.

    Under H0 (no net difference), each discordant pair is equally likely to
    be AB or BA, so n_ab ~ Bin(n_discordant, 0.5). The two-tailed p-value
    is 2 * P(X <= min(n_ab, n_ba)) capped at 1.0.
    """
    n_disc = n_ab + n_ba
    if n_disc == 0:
        return McNemarResult(
            n_ab=n_ab, n_ba=n_ba, n_discordant=0, chi2=0.0, p_value=1.0
        )

    k = min(n_ab, n_ba)
    p_value = min(1.0, 2 * _binom_cdf_half(k, n_disc))
    chi2 = (n_ab - n_ba) ** 2 / n_disc  # approximation; prefer exact p_value

    return McNemarResult(
        n_ab=n_ab,
        n_ba=n_ba,
        n_discordant=n_disc,
        chi2=chi2,
        p_value=p_value,
    )


# ---------------------------------------------------------------------------
# Holm step-down correction
# ---------------------------------------------------------------------------


def holm_correction(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Holm's step-down correction for multiple comparisons.

    Returns a bool list, True where H0 is rejected at the family-wise alpha
    level. More powerful than Bonferroni; controls FWER under any dependence.
    """
    m = len(p_values)
    if m == 0:
        return []

    rejected = [False] * m
    order = sorted(range(m), key=lambda i: p_values[i])

    for rank, idx in enumerate(order):
        threshold = alpha / (m - rank)
        if p_values[idx] <= threshold:
            rejected[idx] = True
        else:
            break  # step-down: once we fail to reject, all remaining are kept

    return rejected


# ---------------------------------------------------------------------------
# Cochran's Q test
# ---------------------------------------------------------------------------


def cochrans_q(matrix: list[list[bool]]) -> tuple[float, int]:
    """Cochran's Q test for K related dichotomous outcomes.

    matrix[i][j] = True/False for subject i (case family) under condition j
    (e.g., tool ordering). Returns (Q statistic, df = K-1). Under H0,
    Q is approximately chi-squared(df).

    Use for order or paraphrase sweeps with more than two conditions.
    For exactly two conditions, prefer mcnemar_test.
    """
    n = len(matrix)
    if n == 0:
        return (0.0, 0)
    k = len(matrix[0]) if matrix else 0
    if k <= 1:
        return (0.0, 0)

    row_totals = [sum(row) for row in matrix]
    col_totals = [sum(matrix[i][j] for i in range(n)) for j in range(k)]
    T = sum(row_totals)

    numerator = (k - 1) * (k * sum(c * c for c in col_totals) - T * T)
    denominator = k * T - sum(r * r for r in row_totals)

    if denominator == 0:
        return (0.0, k - 1)

    return (numerator / denominator, k - 1)
