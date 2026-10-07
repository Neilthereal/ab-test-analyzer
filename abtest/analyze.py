"""Orchestration: run the full analysis and reach a verdict.

Pipeline per experiment:
    1. SRM check  -- if traffic split is broken, the result is INVALID
                    regardless of the p-value.
    2. z-test     -- significance of the conversion-rate difference.
    3. Verdict    -- SHIP / DO NOT SHIP / INCONCLUSIVE, plus the sample
                    size needed to resolve an inconclusive test.
"""

from dataclasses import dataclass, field

from .data import Experiment
from .stats import required_sample_size, srm_check, two_proportion_ztest

SRM_ALPHA = 0.01  # stricter bar: SRM is a data-quality gate, not the test itself


@dataclass
class AnalysisResult:
    experiment: Experiment
    alpha: float
    rates: dict = field(default_factory=dict)
    srm: dict = field(default_factory=dict)
    test: dict = field(default_factory=dict)
    verdict: str = ""
    verdict_reason: str = ""
    significant: bool = False
    srm_failed: bool = False
    required_n_per_group: int = 0  # to detect the observed uplift at 80% power


def analyze(exp: Experiment, alpha: float = 0.05) -> AnalysisResult:
    res = AnalysisResult(experiment=exp, alpha=alpha)
    res.srm = srm_check(exp.n_control, exp.n_variant)
    res.srm_failed = res.srm["p_value"] < SRM_ALPHA
    res.test = two_proportion_ztest(exp.x_control, exp.n_control,
                                    exp.x_variant, exp.n_variant)
    res.significant = res.test["p_value"] < alpha
    diff = res.test["diff"]

    if res.srm_failed:
        res.verdict = "INVALID"
        res.verdict_reason = (
            "Sample Ratio Mismatch: traffic split deviates from 50/50 "
            f"(p={res.srm['p_value']:.4f}). Randomization is broken; "
            "the result cannot be trusted."
        )
    elif res.significant and diff > 0:
        res.verdict = "SHIP IT"
        res.verdict_reason = (
            f"Variant wins with {res.test['uplift']:.1%} relative uplift "
            f"(p={res.test['p_value']:.4f} < {alpha})."
        )
    elif res.significant and diff < 0:
        res.verdict = "DO NOT SHIP"
        res.verdict_reason = (
            f"Variant loses by {abs(res.test['uplift']):.1%} relative "
            f"(p={res.test['p_value']:.4f} < {alpha})."
        )
    else:
        res.verdict = "INCONCLUSIVE"
        # How many users per group would it take to detect what we saw?
        uplift = abs(res.test["uplift"])
        if uplift > 0 and res.test["p1"] > 0:
            res.required_n_per_group = required_sample_size(
                res.test["p1"], uplift, alpha=alpha, power=0.8)
            res.verdict_reason = (
                f"No significant difference (p={res.test['p_value']:.3f} >= {alpha}). "
                f"To detect the observed {uplift:.1%} uplift at 80% power you would need "
                f"~{res.required_n_per_group:,} users per group."
            )
        else:
            res.verdict_reason = (
                f"No significant difference (p={res.test['p_value']:.3f} >= {alpha}); "
                "the variant shows no measurable effect."
            )
    return res
