#!/usr/bin/env python3
"""CLI: analyze one A/B test dataset and write a Markdown report.

Usage:
    python3 run.py datasets/checkout_button.csv
    python3 run.py datasets/pricing_page.csv --alpha 0.01 --out report.md
"""

import argparse
import sys

from abtest.analyze import analyze
from abtest.data import load_dataset
from abtest.report import render_console, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze an A/B test dataset.")
    parser.add_argument("dataset", help="path to a .csv or .json dataset")
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="significance level (default 0.05)")
    parser.add_argument("--out", default="report.md",
                        help="where to write the Markdown report")
    args = parser.parse_args()

    try:
        exp = load_dataset(args.dataset)
    except (ValueError, FileNotFoundError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    res = analyze(exp, alpha=args.alpha)
    print(render_console(res))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_markdown(res))
    print(f"report written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
