"""CLI: train forecasting models.

Examples (run from ``backend/`` with the venv active)::

    python -m ml.train                          # top products, both models
    python -m ml.train --model prophet
    python -m ml.train --model xgboost
    python -m ml.train --model all
    python -m ml.train --product SKU-1000       # sku or uuid
    python -m ml.train --product all --max-series 20
    python -m ml.train --warehouse <uuid>       # product x warehouse series
"""

from __future__ import annotations

import argparse
import json
import sys

from ml.config import load_config, resolve_path
from ml.data.loaders import load_product_index, normalize_id
from ml.exceptions import MLError
from ml.pipeline.training import train_all


def _fmt(value: object) -> str:
    return "-" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)


def _resolve_products(args: argparse.Namespace, cfg) -> list[str] | None:
    if not args.product or args.product == ["all"]:
        return None  # ranked + capped inside train_all
    resolved: list[str] = []
    sku_index = None
    for item in args.product:
        norm = normalize_id(item)
        if norm and "-" in norm and len(norm) == 36:
            resolved.append(norm)
            continue
        if sku_index is None:
            if cfg.data.source != "sqlite":
                raise MLError(
                    f"'{item}' is not a UUID and SKU lookup needs the sqlite source"
                )
            sku_index = load_product_index(cfg.data.sqlite_path)
        match = sku_index[sku_index["sku"].str.lower() == item.lower()]
        if match.empty:
            raise MLError(f"Unknown product '{item}' (not a UUID or known SKU)")
        resolved.append(str(match.iloc[0]["product_id"]))
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.train", description="Train demand-forecasting models"
    )
    parser.add_argument(
        "--model",
        choices=["prophet", "xgboost", "all"],
        default="all",
        help="which model(s) to train (default: all)",
    )
    parser.add_argument(
        "--product",
        nargs="*",
        default=None,
        help="product uuid(s) or sku(s), or 'all' (default: top by demand)",
    )
    parser.add_argument(
        "--warehouse",
        default=None,
        help="warehouse uuid — train product x warehouse series",
    )
    parser.add_argument(
        "--max-series", type=int, default=None, help="cap the number of series"
    )
    parser.add_argument("--config", default=None, help="path to a config yaml")
    parser.add_argument(
        "--json", action="store_true", help="print the full batch report as JSON"
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    models = None if args.model == "all" else [args.model]

    try:
        products = _resolve_products(args, cfg)
        report = train_all(
            cfg,
            product_ids=products,
            warehouse_id=normalize_id(args.warehouse) if args.warehouse else None,
            models=models,
            max_series=args.max_series,
        )
    except MLError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print(f"Dataset:  {report['dataset']}  (version {report['dataset_version']})")
    print(f"Trained:  {len(report['trained'])} series"
          f"   Skipped: {len(report['skipped'])}")
    print()
    header = (
        f"{'series':<44} {'model':<9} {'MAE':>8} {'RMSE':>8} "
        f"{'MAPE%':>8} {'sMAPE%':>8} {'WAPE%':>8}  best"
    )
    print(header)
    print("-" * len(header))
    for rec in report["trained"]:
        for model_name, metrics in rec["metrics"].items():
            if metrics is None:
                line = (
                    f"{rec['series_key'][:44]:<44} {model_name:<9} "
                    f"{'FAILED: ' + rec['errors'].get(model_name, '?')}"
                )
            else:
                star = "  *" if model_name == rec["best_model"] else ""
                line = (
                    f"{rec['series_key'][:44]:<44} {model_name:<9} "
                    f"{_fmt(metrics['mae']):>8} {_fmt(metrics['rmse']):>8} "
                    f"{_fmt(metrics['mape']):>8} {_fmt(metrics['smape']):>8} "
                    f"{_fmt(metrics['wape']):>8}{star}"
                )
            print(line)
    print()
    for rec in report["trained"]:
        print(f"  {rec['series_key']}: best={rec['best_model']} "
              f"({rec['selection_reason']})")
    for skip in report["skipped"]:
        print(f"  SKIPPED {skip['product_id']}: {skip['reason']}")
    print(f"\nModels saved under: {resolve_path(cfg.paths.models_dir)}")
    print(f"Experiments logged: "
          f"{resolve_path(cfg.paths.artifacts_dir) / 'evaluation'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
