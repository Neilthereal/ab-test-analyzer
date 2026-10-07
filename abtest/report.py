"""Markdown report generation for an A/B test analysis."""

from .analyze import AnalysisResult


def _pct(x: float) -> str:
    return f"{x:.2%}"


def render_markdown(res: AnalysisResult) -> str:
    exp, t, srm = res.experiment, res.test, res.srm
    lo, hi = t["diff_ci"]
    lines = [
        f"# A/B Test Report: {exp.name}",
        "",
        f"**Verdict: {res.verdict}**",
        "",
        res.verdict_reason,
        "",
        "## Conversion rates",
        "",
        "| Group | Visitors | Conversions | Rate |",
        "|-------|----------|-------------|------|",
        f"| {exp.control_name} | {exp.n_control:,} | {exp.x_control:,} | {_pct(t['p1'])} |",
        f"| {exp.variant_name} | {exp.n_variant:,} | {exp.x_variant:,} | {_pct(t['p2'])} |",
        "",
        "## Statistical test",
        "",
        f"- Absolute difference: {_pct(t['diff'])} (95% CI: {_pct(lo)} to {_pct(hi)})",
        f"- Relative uplift: {t['uplift']:+.2%}",
        f"- z-statistic: {t['z']:.3f}",
        f"- Two-sided p-value: {t['p_value']:.4f} (alpha = {res.alpha})",
        f"- Significant: {'yes' if res.significant else 'no'}",
        "",
        "## Sample Ratio Mismatch check",
        "",
        f"- Observed split: {_pct(srm['split'][0])} / {_pct(srm['split'][1])}",
        f"- Chi-square p-value: {srm['p_value']:.4f} "
        f"({'FAIL -- randomization broken' if res.srm_failed else 'pass'})",
        "",
        "_Method: two-proportion z-test (pooled SE), Wald 95% CI (unpooled SE), "
        "chi-square SRM check. Binary conversion outcomes only._",
        "",
    ]
    return "\n".join(lines)


def render_console(res: AnalysisResult) -> str:
    exp, t = res.experiment, res.test
    lo, hi = t["diff_ci"]
    return (
        f"[{exp.name}] {exp.control_name}: {_pct(t['p1'])} ({exp.x_control:,}/{exp.n_control:,})"
        f"  vs  {exp.variant_name}: {_pct(t['p2'])} ({exp.x_variant:,}/{exp.n_variant:,})\n"
        f"  uplift {t['uplift']:+.2%}  (95% CI {_pct(lo)} to {_pct(hi)})"
        f"  p={t['p_value']:.4f}  SRM={'FAIL' if res.srm_failed else 'ok'}"
        f"  => {res.verdict}"
    )
