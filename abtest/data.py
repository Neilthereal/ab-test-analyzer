"""Loading and validation of experiment datasets.

Supported formats (exactly two groups: control and variant):

CSV, with header ``group,visitors,conversions``::

    group,visitors,conversions
    control,10000,1200
    variant,10000,1350

JSON, a list of two objects::

    [{"group": "control", "visitors": 10000, "conversions": 1200},
     {"group": "variant", "visitors": 10000, "conversions": 1350}]
"""

import csv
import json
from dataclasses import dataclass


@dataclass
class Experiment:
    name: str
    control_name: str
    variant_name: str
    n_control: int
    x_control: int
    n_variant: int
    x_variant: int


def _validate_row(group: str, visitors, conversions) -> tuple:
    try:
        n = int(visitors)
        x = int(conversions)
    except (TypeError, ValueError):
        raise ValueError(f"group '{group}': visitors/conversions must be integers")
    if n <= 0:
        raise ValueError(f"group '{group}': visitors must be positive")
    if not 0 <= x <= n:
        raise ValueError(f"group '{group}': conversions must be between 0 and visitors")
    return n, x


def load_dataset(path: str, name: str = None) -> Experiment:
    """Load an experiment dataset from a CSV or JSON file."""
    name = name or path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list) or len(rows) != 2:
            raise ValueError("JSON dataset must be a list of exactly 2 group objects")
        parsed = [(r["group"], r["visitors"], r["conversions"]) for r in rows]
    elif path.endswith(".csv"):
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if set(reader.fieldnames or []) != {"group", "visitors", "conversions"}:
                raise ValueError("CSV header must be exactly: group,visitors,conversions")
            parsed = [(r["group"], r["visitors"], r["conversions"]) for r in reader]
        if len(parsed) != 2:
            raise ValueError(f"expected exactly 2 groups, got {len(parsed)}")
    else:
        raise ValueError("unsupported file type (use .csv or .json)")

    (g1, n1, x1), (g2, n2, x2) = parsed
    n1, x1 = _validate_row(g1, n1, x1)
    n2, x2 = _validate_row(g2, n2, x2)
    if g1 == g2:
        raise ValueError("group names must be distinct")
    return Experiment(name=name, control_name=g1, variant_name=g2,
                      n_control=n1, x_control=x1, n_variant=n2, x_variant=x2)
