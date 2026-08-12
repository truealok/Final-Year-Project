"""CLI: forecast demand with a trained model.

Examples::

    python -m ml.predict --product SKU-1000 --days 30
    python -m ml.predict --product <uuid> --warehouse <uuid> --days 14
    python -m ml.predict --product SKU-1000 --start 2026-09-01 --end 2026-09-30
    python -m ml.predict --product SKU-1000 --model prophet
"""

from __future__ import annotations

import argparse
import json
import sys

from ml.config import load_config
from ml.data.loaders import load_product_index, normalize_id
from ml.exceptions import MLError
from ml.pipeline.prediction import predict_demand


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.predict", description="Predict demand"
    )
    parser.add_argument("--product", required=True, help="product uuid or sku")
    parser.add_argument("--warehouse", default=None, help="warehouse uuid")
    parser.add_argument("--days", type=int, default=None, help="forecast horizon")
    parser.add_argument("--start", default=None, help="start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="end date YYYY-MM-DD")
    parser.add_argument(
        "--model", choices=["prophet", "xgboost"], default=None,
        help="force a model type (default: best for the series)",
    )
    parser.add_argument("--config", default=None, help="path to a config yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)

    product = normalize_id(args.product)
    # allow SKU lookup for convenience
    if product and not (len(product) == 36 and "-" in product):
        if cfg.data.source == "sqlite":
            idx = load_product_index(cfg.data.sqlite_path)
            match = idx[idx["sku"].str.lower() == product.lower()]
            if match.empty:
                print(f"ERROR: unknown product '{args.product}'", file=sys.stderr)
                return 1
            product = str(match.iloc[0]["product_id"])

    try:
        result = predict_demand(
            product,
            warehouse_id=args.warehouse,
            forecast_days=args.days,
            start_date=args.start,
            end_date=args.end,
            model_type=args.model,
            cfg=cfg,
        )
    except MLError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
