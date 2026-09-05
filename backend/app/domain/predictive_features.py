from datetime import timedelta
from enum import StrEnum
from math import isfinite

PREDICTIVE_FEATURE_VERSION = "v1"


class PredictiveFeatureWindow(StrEnum):
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"


PREDICTIVE_FEATURE_WINDOW_DURATIONS = {
    PredictiveFeatureWindow.ONE_HOUR: timedelta(hours=1),
    PredictiveFeatureWindow.SIX_HOURS: timedelta(hours=6),
    PredictiveFeatureWindow.TWENTY_FOUR_HOURS: timedelta(hours=24),
    PredictiveFeatureWindow.SEVEN_DAYS: timedelta(days=7),
}


class FeatureCoverageStatus(StrEnum):
    NO_DATA = "NO_DATA"
    SPARSE = "SPARSE"
    SUFFICIENT = "SUFFICIENT"


class PredictiveFeatureConfigurationError(RuntimeError):
    """Raised when persisted configuration cannot produce valid features."""


class PredictiveFeatureDataError(RuntimeError):
    """Raised when stored telemetry cannot produce finite features."""


def classify_coverage(reading_count: int) -> FeatureCoverageStatus:
    if reading_count == 0:
        return FeatureCoverageStatus.NO_DATA
    if reading_count < 5:
        return FeatureCoverageStatus.SPARSE
    return FeatureCoverageStatus.SUFFICIENT


def safe_percent_change(first_value: float, last_value: float) -> float | None:
    if first_value == 0:
        return None
    return (last_value - first_value) / abs(first_value) * 100


def require_positive_finite_threshold(threshold: float) -> float:
    if not isfinite(threshold) or threshold <= 0:
        raise PredictiveFeatureConfigurationError(
            "Persisted alert threshold must be positive and finite"
        )
    return threshold


def require_finite(value: float | None, *, feature_name: str) -> float | None:
    if value is not None and not isfinite(value):
        raise PredictiveFeatureDataError(f"Non-finite {feature_name} feature")
    return value
