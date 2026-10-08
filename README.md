# ab-test-analyzer

A zero-dependency A/B test analyzer: feed it per-group visitor/conversion counts,
get a statistical verdict (ship / don't ship / inconclusive / invalid) with a
Markdown report. Python 3.10+, standard library only.

## Quick start

```bash
python3 run.py datasets/checkout_button.csv
python3 run.py datasets/pricing_page.csv --alpha 0.01 --out report.md
python3 -m unittest discover -s tests   # 12 tests
```

## What it does

For each experiment it runs, in order:

1. **Sample Ratio Mismatch (SRM) check** -- chi-square goodness-of-fit against the
   expected 50/50 traffic split. If randomization broke, the verdict is `INVALID`
   no matter how small the p-value is.
2. **Two-proportion z-test** (pooled standard error) with two-sided p-value,
   plus a Wald 95% confidence interval for the absolute difference (unpooled SE)
   and the relative uplift.
3. **Verdict**:
   - `SHIP IT` -- significant and positive
   - `DO NOT SHIP` -- significant and negative
   - `INCONCLUSIVE` -- not significant; reports the per-group sample size needed
     to detect the observed uplift at 80% power
   - `INVALID` -- SRM detected

4. **Sample-size calculator** -- per-group n required to detect a target minimum
   detectable effect (MDE) at a given alpha/power.

## Sample output

```
[checkout_button] control: 12.00% (1,200/10,000)  vs  variant: 13.50% (1,350/10,000)
  uplift +12.50%  (95% CI 0.58% to 2.42%)  p=0.0015  SRM=ok  => SHIP IT

[pricing_page] control: 12.00% (960/8,000)  vs  variant: 12.62% (1,010/8,000)
  uplift +5.21%  (95% CI -0.39% to 1.64%)  p=0.2290  SRM=ok  => INCONCLUSIVE

[broken_randomization] control: 11.80% (1,180/10,000)  vs  variant: 13.23% (820/6,200)
  uplift +12.08%  (95% CI 0.37% to 2.48%)  p=0.0073  SRM=FAIL  => INVALID
```

The third case is the interesting one: p=0.0073 looks like a win, but the
traffic split (10,000 vs 6,200) fails the SRM check, so the tool refuses to
call it -- a significant p-value on broken randomization is worse than useless.

## Project structure

```
abtest/
  stats.py    # z-test, CI, uplift, SRM check, sample-size calculator
  data.py     # CSV/JSON loading + validation
  analyze.py  # pipeline orchestration and verdict logic
  report.py   # Markdown + console rendering
datasets/     # 3 sample experiments (win / inconclusive / broken randomization)
tests/        # 12 unit tests (stdlib unittest)
run.py        # CLI
```

## Input format

CSV with header `group,visitors,conversions` (exactly 2 groups), or JSON list
of two `{"group", "visitors", "conversions"}` objects.

## Limitations

Binary conversion outcomes only; no sequential testing / peeking correction;
no multiple-comparison correction; fixed-horizon design. Natural extensions:
Welch's t-test for continuous metrics, CUPED variance reduction, sequential
monitoring with alpha spending.
