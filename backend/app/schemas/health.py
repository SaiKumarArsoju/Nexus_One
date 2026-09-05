from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import SensorType
from app.domain.health_scoring import HealthBand, HealthConfidence
from app.domain.predictive_features import FeatureCoverageStatus, PredictiveFeatureWindow


class MachineHealthResponse(BaseModel):
    machine_name: str
    status: str
    overall_health: int
    temperature: float | None = None
    pressure: float | None = None
    vibration: float | None = None
    rpm: float | None = None
    energy: float | None = None
    warnings: list[str]
    recommendation: str


class SensorHealthPenaltyResponse(BaseModel):
    threshold_proximity: float
    mean_level: float
    exceedance: float
    trend: float
    variability: float


class SensorHealthScoreResponse(BaseModel):
    sensor_id: UUID
    sensor_name: str
    sensor_type: SensorType
    unit: str
    health_score: float | None
    health_band: HealthBand
    confidence: HealthConfidence
    threshold_value: float
    component_penalties: SensorHealthPenaltyResponse
    reasons: list[str]
    coverage_status: FeatureCoverageStatus


class MachineHealthScoreResponse(BaseModel):
    indicator_type: str
    feature_version: str
    scoring_version: str
    machine_id: UUID
    window: PredictiveFeatureWindow
    window_start: datetime
    window_end: datetime
    health_score: float | None
    health_band: HealthBand
    confidence: HealthConfidence
    scored_sensor_count: int
    total_sensor_count: int
    most_concerning_sensor_id: UUID | None
    lowest_sensor_score: float | None
    sensor_scores: list[SensorHealthScoreResponse]
    reasons: list[str]
