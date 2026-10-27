"""U3 tests: Wilson interval, clustered bootstrap, McNemar's test, Holm correction.

All values verified by hand before writing the assertions.
"""

from surfacelab.stats import (
    BootstrapCI,
    _binom_cdf_half,
    _binom_pmf,
    _trial_bootstrap_BROKEN,
    clustered_bootstrap,
    cochrans_q,
    holm_correction,
    mcnemar_test,
    wilson_interval,
)

# ---------------------------------------------------------------------------
# Wilson interval — hand-computed ground truth
#
# Formula: center = (s + z²/2) / (n + z²),
#          margin = z * sqrt(n*p̂*(1-p̂) + z²/4) / (n + z²)
# z = 1.959964, z² = 3.84147
# ---------------------------------------------------------------------------


def test_wilson_18_of_27() -> None:
    # denom=30.841, center=0.6459, margin=0.1677 → (0.4782, 0.8136)
    lo, hi = wilson_interval(18, 27)
    assert abs(lo - 0.4782) < 0.001
    assert abs(hi - 0.8136) < 0.001


def test_wilson_8_of_27() -> None:
    # denom=30.841, center=0.3217, margin=0.1632 → (0.1585, 0.4849)
    lo, hi = wilson_interval(8, 27)
    assert abs(lo - 0.1585) < 0.001
    assert abs(hi - 0.4849) < 0.001


def test_wilson_intervals_overlap_despite_different_rates() -> None:
    """18/27 and 8/27 have overlapping 95% CIs — must use a paired test."""
    lo_a, _ = wilson_interval(18, 27)
    _, hi_b = wilson_interval(8, 27)
    # Upper of 8/27 (~0.4849) exceeds lower of 18/27 (~0.4782)
    assert hi_b > lo_a


def test_wilson_zero_trials_returns_full_interval() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_wilson_all_correct() -> None:
    lo, hi = wilson_interval(10, 10)
    assert lo > 0.7  # Wilson shrinks away from boundary
    assert hi == 1.0


def test_wilson_none_correct() -> None:
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0
    assert hi < 0.3


def test_wilson_bounds_in_unit_interval() -> None:
    lo, hi = wilson_interval(5, 20)
    assert 0.0 <= lo <= hi <= 1.0


# ---------------------------------------------------------------------------
# Binomial helpers — exact values
# ---------------------------------------------------------------------------


def test_binom_pmf_fair_coin() -> None:
    # P(X=3 | n=6, p=0.5) = C(6,3)/2^6 = 20/64
    assert abs(_binom_pmf(3, 6) - 20 / 64) < 1e-12


def test_binom_cdf_half_exact() -> None:
    # P(X<=1 | n=6, p=0.5) = (C(6,0)+C(6,1))/64 = 7/64
    assert abs(_binom_cdf_half(1, 6) - 7 / 64) < 1e-12


def test_binom_cdf_half_full() -> None:
    # P(X<=n | n, 0.5) = 1
    assert abs(_binom_cdf_half(6, 6) - 1.0) < 1e-12


# ---------------------------------------------------------------------------
# McNemar's exact test — hand-computed ground truth
# ---------------------------------------------------------------------------


def test_mcnemar_balanced_discordant_pairs() -> None:
    # n_ab=3, n_ba=3: k=3, P(X<=3|n=6)=42/64; 2*42/64=84/64>1 → p=1.0
    r = mcnemar_test(3, 3)
    assert r.p_value == 1.0
    assert r.chi2 == 0.0


def test_mcnemar_5_vs_1() -> None:
    # k=1, P(X<=1|n=6)=7/64; p_val=14/64=0.21875
    r = mcnemar_test(5, 1)
    assert abs(r.p_value - 14 / 64) < 1e-12


def test_mcnemar_all_one_way() -> None:
    # n_ab=4, n_ba=0: k=0, P(X=0|n=4)=1/16; p_val=2/16=0.125
    r = mcnemar_test(4, 0)
    assert abs(r.p_value - 0.125) < 1e-12


def test_mcnemar_no_discordant_pairs() -> None:
    r = mcnemar_test(0, 0)
    assert r.p_value == 1.0
    assert r.n_discordant == 0


def test_mcnemar_chi2_symmetric() -> None:
    r1 = mcnemar_test(8, 2)
    r2 = mcnemar_test(2, 8)
    assert r1.chi2 == r2.chi2
    assert r1.p_value == r2.p_value


def test_mcnemar_p_value_in_range() -> None:
    r = mcnemar_test(10, 3)
    assert 0.0 < r.p_value <= 1.0


def test_mcnemar_n_discordant_correct() -> None:
    r = mcnemar_test(7, 3)
    assert r.n_discordant == 10


# ---------------------------------------------------------------------------
# Clustered bootstrap
# ---------------------------------------------------------------------------


def _correlated_families() -> list[list[bool]]:
    """5 families × 3 trials. Outcomes perfectly correlated within families.
    Point accuracy = 9/15 = 0.6.
    """
    return [
        [True, True, True],
        [True, True, True],
        [False, False, False],
        [False, False, False],
        [True, True, True],
    ]


def test_clustered_bootstrap_point_estimate() -> None:
    result = clustered_bootstrap(_correlated_families(), seed=42)
    assert abs(result.point - 0.6) < 1e-9


def test_clustered_bootstrap_interval_contains_truth() -> None:
    result = clustered_bootstrap(_correlated_families(), seed=42)
    assert result.lower <= 0.6 <= result.upper


def test_clustered_bootstrap_wider_than_trial_bootstrap() -> None:
    """Clustered CI is wider than naive trial CI on correlated families.

    This is the break-it target: changing clustered_bootstrap to resample
    individual trials (like _trial_bootstrap_BROKEN) makes this test fail.
    """
    fams = _correlated_families()
    family_ci = clustered_bootstrap(fams, seed=42)
    trial_ci = _trial_bootstrap_BROKEN(fams, seed=42)
    family_width = family_ci.upper - family_ci.lower
    trial_width = trial_ci.upper - trial_ci.lower
    assert family_width > trial_width, (
        f"Clustered CI ({family_width:.3f}) should be wider than "
        f"trial CI ({trial_width:.3f}) on perfectly correlated families"
    )


def test_clustered_bootstrap_bounds_in_range() -> None:
    fams = [[True, False], [True, True], [False, False]]
    result = clustered_bootstrap(fams, seed=7)
    assert 0.0 <= result.lower <= result.upper <= 1.0


def test_clustered_bootstrap_deterministic_with_seed() -> None:
    fams = _correlated_families()
    assert clustered_bootstrap(fams, seed=42) == clustered_bootstrap(fams, seed=42)


def test_clustered_bootstrap_empty_families() -> None:
    result = clustered_bootstrap([], seed=0)
    assert result == BootstrapCI(lower=0.0, upper=1.0, point=0.0)


# ---------------------------------------------------------------------------
# Holm step-down correction — hand-computed ground truth
# ---------------------------------------------------------------------------


def test_holm_basic() -> None:
    # p=[0.01, 0.04, 0.03], sorted order: idx0(0.01), idx2(0.03), idx1(0.04)
    # rank 0: 0.01 <= 0.05/3=0.0167 → reject idx0
    # rank 1: 0.03 > 0.05/2=0.025 → stop
    assert holm_correction([0.01, 0.04, 0.03]) == [True, False, False]


def test_holm_all_significant() -> None:
    # thresholds: 0.05/3, 0.05/2, 0.05/1; all p < each threshold
    assert holm_correction([0.001, 0.002, 0.003]) == [True, True, True]


def test_holm_none_significant() -> None:
    assert holm_correction([0.2, 0.3, 0.4]) == [False, False, False]


def test_holm_empty() -> None:
    assert holm_correction([]) == []


def test_holm_single_below_alpha() -> None:
    assert holm_correction([0.03]) == [True]


def test_holm_single_above_alpha() -> None:
    assert holm_correction([0.06]) == [False]


def test_holm_preserves_index_order() -> None:
    # p=[0.04, 0.001, 0.03], sorted: idx1(0.001), idx2(0.03), idx0(0.04)
    # rank 0: 0.001 <= 0.05/3 → reject idx1
    # rank 1: 0.03 > 0.05/2=0.025 → stop
    rejected = holm_correction([0.04, 0.001, 0.03])
    assert rejected[0] is False
    assert rejected[1] is True
    assert rejected[2] is False


# ---------------------------------------------------------------------------
# Cochran's Q — basic smoke tests
# ---------------------------------------------------------------------------


def test_cochrans_q_identical_conditions() -> None:
    # If all conditions give the same outcome, Q = 0.
    matrix = [[True, True, True], [False, False, False], [True, True, True]]
    Q, df = cochrans_q(matrix)
    assert Q == 0.0
    assert df == 2


def test_cochrans_q_two_conditions_agrees_with_mcnemar() -> None:
    # 3 subjects, condition A: [T,T,F], condition B: [F,T,T]
    # n_AB=1 (subject 0: A=T,B=F), n_BA=1 (subject 2: A=F,B=T)
    # McNemar Q = (1-1)^2 / (1+1) = 0; Cochran's Q should also be 0.
    matrix = [[True, False], [True, True], [False, True]]
    Q, df = cochrans_q(matrix)
    assert df == 1
    # With balanced discordant pairs, Q = 0
    assert abs(Q) < 1e-9


def test_cochrans_q_empty_matrix() -> None:
    Q, df = cochrans_q([])
    assert Q == 0.0
    assert df == 0


def test_cochrans_q_single_condition() -> None:
    _Q, df = cochrans_q([[True], [False], [True]])
    assert df == 0
