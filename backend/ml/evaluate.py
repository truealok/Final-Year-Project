"""CLI: inspect trained models and the experiment log.

Examples::

    python -m ml.evaluate                 # comparison table of trained series
    python -m ml.evaluate --experiments   # raw experiment log
    python -m ml.evaluate --summary       # per-model-type aggregates
"""

from __future__ import annotations

import argparse
import json

from ml.config import load_config, resolve_path
from ml.pipeline.prediction import get_registry


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ml.evaluate",
        description="Show evaluation results for trained models",
    )
    parser.add_argument("--experiments", action="store_true",
                        help="print the raw experiment log")
    parser.add_argument("--summary", action="store_true",
                        help="print per-model-type aggregates (JSON)")
    parser.add_argument("--config", default=None)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    registry = get_registry(cfg)

    if args.experiments:
        path = resolve_path(cfg.paths.artifacts_dir) / "evaluation" / "experiments.jsonl"
        if not path.exists():
            print("No experiments logged yet. Run: python -m ml.train")
            return 0
        for line in path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            print(
                f"{rec['timestamp'][:19]}  {rec['model']:<9} v{rec['version']:<3}"
                f" {rec['series_key'][:40]:<40}"
                f" mae={_fmt(rec['mae'])} rmse={_fmt(rec['rmse'])}"
                f" wape={_fmt(rec['wape'])} ({rec['training_seconds']}s)"
            )
        return 0

    if args.summary:
        print(json.dumps(registry.summary(), indent=2, default=str))
        return 0

    series = registry.list_series()
    if not series:
        print("No trained models yet. Run: python -m ml.train")
        return 0

    header = (
        f"{'series':<44} {'best':<9} {'MAE':>8} {'RMSE':>8} "
        f"{'MAPE%':>8} {'sMAPE%':>8} {'WAPE%':>8}  reason"
    )
    print(header)
    print("-" * len(header))
    for key in series:
        best = registry.best_info(key)
        m = best.get("metrics", {})
        print(
            f"{key[:44]:<44} {best['model_type']:<9} "
            f"{_fmt(m.get('mae')):>8} {_fmt(m.get('rmse')):>8} "
            f"{_fmt(m.get('mape')):>8} {_fmt(m.get('smape')):>8} "
            f"{_fmt(m.get('wape')):>8}  {best.get('reason', '')[:60]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
