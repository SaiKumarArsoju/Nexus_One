from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.health_scoring import HealthBand, HealthConfidence
from app.domain.maintenance_intelligence import (
    MaintenanceAction,
    MaintenanceEvidenceType,
    MaintenancePriority,
)
from app.domain.predictive_features import PredictiveFeatureWindow
from app.models import AlertSeverity


class MaintenanceEvidenceResponse(BaseModel):
    type: MaintenanceEvidenceType
    message: str
    sensor_id: UUID | None = None
    sensor_name: str | None = None
    alert_id: UUID | None = None
    severity: AlertSeverity | None = None


class MachineMaintenanceAssessmentResponse(BaseModel):
    indicator_type: str
    feature_version: str
    scoring_version: str
    maintenance_policy_version: str
    machine_id: UUID
    window: PredictiveFeatureWindow
    window_start: datetime
    window_end: datetime
    health_score: float | None
    health_band: HealthBand
    confidence: HealthConfidence
    maintenance_priority: MaintenancePriority
    unresolved_alert_count: int
    critical_alert_count: int
    warning_alert_count: int
    most_concerning_sensor_id: UUID | None
    most_concerning_sensor_name: str | None
    evidence: list[MaintenanceEvidenceResponse]
    recommended_actions: list[MaintenanceAction]
    reasons: list[str]
