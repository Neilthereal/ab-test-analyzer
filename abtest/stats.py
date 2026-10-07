"""Core statistics for A/B testing. Standard library only.

Implements the standard frequentist toolkit for comparing two conversion
rates:

- two-proportion z-test (pooled standard error) with two-sided p-value
- Wald 95% confidence interval for the absolute difference (unpooled SE)
- relative uplift and its confidence interval
- Sample Ratio Mismatch (SRM) check via chi-square goodness-of-fit
- per-group sample-size calculator for a target minimum detectable effect

All p-values come from the standard normal CDF, computed with math.erf,
so there are no third-party dependencies (no scipy needed).
"""

import math

Z_95 = 1.959963984540054   # two-sided 95% critical value
Z_80_POWER = 0.8416212335729143  # z for 80% statistical power


def norm_cdf(x: float) -> float:
    """Standard normal CDF, via the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_proportion_ztest(x1: int, n1: int, x2: int, n2: int) -> dict:
    """Two-sided z-test for the difference between two conversion rates.

    Group 1 is the control, group 2 the variant. Returns rates, the absolute
    difference, a 95% confidence interval, the z-statistic, the two-sided
    p-value, and the relative uplift.
    """
    p1 = x1 / n1
    p2 = x2 / n2
    diff = p2 - p1

    # Pooled SE for the hypothesis test (H0: p1 == p2).
    p_pool = (x1 + x2) / (n1 + n2)
    se_pooled = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = diff / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * (1 - norm_cdf(abs(z)))
    p_value = min(max(p_value, 0.0), 1.0)

    # Unpooled SE for the confidence interval (no H0 assumption).
    se_diff = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    ci_lo = diff - Z_95 * se_diff
    ci_hi = diff + Z_95 * se_diff

    uplift = diff / p1 if p1 > 0 else float("inf")

    return {
        "p1": p1,
        "p2": p2,
        "diff": diff,
        "diff_ci": (ci_lo, ci_hi),
        "z": z,
        "p_value": p_value,
        "uplift": uplift,
    }


def srm_check(n1: int, n2: int) -> dict:
    """Sample Ratio Mismatch check.

    Tests whether the observed traffic split deviates from the expected
    50/50 allocation using a chi-square goodness-of-fit test (1 df).
    A significant SRM means the randomization broke and the result
    cannot be trusted, no matter how small the p-value is.
    """
    total = n1 + n2
    expected = total / 2
    chi2 = (n1 - expected) ** 2 / expected + (n2 - expected) ** 2 / expected
    # For 1 df, chi-square survival function == 2 * (1 - Phi(sqrt(chi2))).
    p_value = 2 * (1 - norm_cdf(math.sqrt(chi2)))
    return {"chi2": chi2, "p_value": p_value, "split": (n1 / total, n2 / total)}


def required_sample_size(p1: float, mde_relative: float,
                         alpha: float = 0.05, power: float = 0.8) -> int:
    """Per-group sample size needed to detect a relative uplift.

    Args:
        p1: baseline conversion rate.
        mde_relative: minimum detectable effect as a fraction, e.g. 0.05
            for a 5% relative uplift.
        alpha: significance level (two-sided).
        power: desired statistical power (1 - beta).

    Uses the standard two-proportion power formula. Only 95%/80% and a
    few common alpha/power combos are tabulated; anything else raises.
    """
    z_alpha = {0.10: 1.6448536269514729, 0.05: Z_95,
               0.01: 2.5758293035489004}.get(alpha)
    z_beta = {0.8: Z_80_POWER, 0.9: 1.2815515655446004}.get(power)
    if z_alpha is None or z_beta is None:
        raise ValueError("supported alpha: 0.10/0.05/0.01; power: 0.8/0.9")
    p2 = p1 * (1 + mde_relative)
    delta = abs(p2 - p1)
    if delta == 0:
        raise ValueError("mde_relative must be non-zero")
    p_bar = (p1 + p2) / 2
    n = ((z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
          + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (delta ** 2)
    return math.ceil(n)
