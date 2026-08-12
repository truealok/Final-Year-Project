"""ResiliChain AI — Machine Learning module.

Demand-forecasting and intelligence layer for the ResiliChain AI platform.

Sub-packages
------------
- ``ml.data``      loading, validation, preprocessing, synthetic generator
- ``ml.eda``       exploratory data analysis (figures + data-driven report)
- ``ml.features``  leakage-safe time-series feature engineering
- ``ml.modeling``  Prophet / XGBoost forecasters, evaluation, selection,
                   model registry
- ``ml.explain``   SHAP explainability (XGBoost) and Prophet components
- ``ml.pipeline``  end-to-end training and prediction pipelines

Command-line entry points (run from ``backend/`` with the venv active)::

    python -m ml.eda
    python -m ml.train --model all
    python -m ml.evaluate
    python -m ml.predict --product <uuid-or-sku> --days 30

The module is intentionally independent of FastAPI: training runs standalone
against a CSV file or the project database, and the backend integrates through
:func:`ml.pipeline.prediction.predict_demand`.
"""

__version__ = "1.0.0"
