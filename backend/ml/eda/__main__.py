"""CLI: run exploratory data analysis.

Examples::

    python -m ml.eda                      # dataset from config (sqlite dev.db)
    python -m ml.eda --config my.yaml

Figures and ``eda_report.json`` land in ``ml/artifacts/eda/``.
"""

from __future__ import annotations

import argparse
import sys

from ml.config import load_config, resolve_path
from ml.data.loaders import load_product_index
from ml.eda.report import run_eda
from ml.exceptions import MLError
from ml.pipeline.dataset import load_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.eda", description="Exploratory data analysis"
    )
    parser.add_argument("--config", default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    try:
        df, validation, _ = load_dataset(cfg)
    except MLError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if validation is not None:
        print("=== Dataset validation ===")
        print(validation.summary())
        print()
        out_dir = resolve_path(cfg.paths.artifacts_dir) / "eda"
        out_dir.mkdir(parents=True, exist_ok=True)
        validation.save(out_dir / "validation_report.json")
        if not validation.is_valid:
            print("Dataset is unsuitable — EDA aborted.", file=sys.stderr)
            return 1

    product_index = None
    if cfg.data.source == "sqlite":
        try:
            product_index = load_product_index(cfg.data.sqlite_path)
        except MLError:
            product_index = None

    out_dir = resolve_path(cfg.paths.artifacts_dir) / "eda"
    report = run_eda(df, out_dir, product_index=product_index)

    print("=== EDA conclusions (derived from the data) ===")
    for conclusion in report["conclusions"]:
        print(f"- {conclusion}")
    print(f"\nFigures + eda_report.json saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
