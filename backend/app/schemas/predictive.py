from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import SensorType
from app.domain.predictive_features import (
    FeatureCoverageStatus,
    PredictiveFeatureWindow,
)


class SensorPredictiveFeatureResponse(BaseModel):
    sensor_id: UUID
    sensor_name: str
    sensor_type: SensorType
    unit: str
    window_start: datetime
    window_end: datetime
    reading_count: int
    mean: float | None
    minimum: float | None
    maximum: float | None
    standard_deviation: float | None
    first_value: float | None
    last_value: float | None
    absolute_change: float | None
    percent_change: float | None
    threshold_value: float
    maximum_threshold_ratio: float | None
    mean_threshold_ratio: float | None
    exceeding_reading_count: int
    exceeding_reading_fraction: float | None
    time_span_seconds: float
    coverage_status: FeatureCoverageStatus


class MachinePredictiveFeaturesResponse(BaseModel):
    feature_version: str
    machine_id: UUID
    window: PredictiveFeatureWindow
    window_start: datetime
    window_end: datetime
    sensor_features: list[SensorPredictiveFeatureResponse]
