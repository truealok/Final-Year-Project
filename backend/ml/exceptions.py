"""ML-module exceptions.

All errors raised by the ML layer derive from :class:`MLError` so callers
(CLI, backend adapter, tests) can catch one base class.
"""


class MLError(Exception):
    """Base class for all ML-module errors."""


class DataValidationError(MLError):
    """The dataset failed validation and is unsuitable for training."""


class InsufficientHistoryError(MLError):
    """A series does not have enough history for the requested operation."""


class UnknownSeriesError(MLError):
    """The requested product/warehouse has no data in the dataset."""


class ModelNotTrainedError(MLError):
    """No trained model exists for the requested series/model type."""


class ConfigError(MLError):
    """The ML configuration file is invalid."""
