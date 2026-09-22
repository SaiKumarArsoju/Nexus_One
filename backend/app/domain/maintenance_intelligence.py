from dataclasses import dataclass
from enum import StrEnum

from app.domain.health_scoring import HealthBand, HealthConfidence
from app.models import AlertSeverity

MAINTENANCE_INTELLIGENCE_VERSION = "v1"
MAX_MAINTENANCE_ACTIONS = 3
MAX_MAINTENANCE_REASONS = 5


class MaintenancePriority(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MaintenanceEvidenceType(StrEnum):
    CRITICAL_ALERT = "CRITICAL_ALERT"
    WARNING_ALERT = "WARNING_ALERT"
    LOW_HEALTH_SCORE = "LOW_HEALTH_SCORE"
    CONCERNING_SENSOR = "CONCERNING_SENSOR"
    THRESHOLD_EXCEEDANCE = "THRESHOLD_EXCEEDANCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_TELEMETRY = "MISSING_TELEMETRY"


class MaintenanceAction(StrEnum):
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    REVIEW_OPERATING_CONDITIONS = "REVIEW_OPERATING_CONDITIONS"
    INSPECT_MACHINE = "INSPECT_MACHINE"
    INSPECT_SENSOR_OR_COMPONENT = "INSPECT_SENSOR_OR_COMPONENT"
    SCHEDULE_MAINTENANCE_REVIEW = "SCHEDULE_MAINTENANCE_REVIEW"
    IMMEDIATE_OPERATIONAL_REVIEW = "IMMEDIATE_OPERATIONAL_REVIEW"
    VERIFY_TELEMETRY = "VERIFY_TELEMETRY"


@dataclass(frozen=True)
class MaintenancePolicyInput:
    health_score: float | None
    health_band: HealthBand
    confidence: HealthConfidence
    alert_severities: tuple[AlertSeverity, ...]
    has_concerning_sensor: bool


def classify_maintenance_priority(data: MaintenancePolicyInput) -> MaintenancePriority:
    has_critical = AlertSeverity.CRITICAL in data.alert_severities
    has_warning = AlertSeverity.WARNING in data.alert_severities
    if has_critical:
        return MaintenancePriority.CRITICAL
    if has_warning and data.health_band == HealthBand.ATTENTION:
        return MaintenancePriority.HIGH
    if has_warning or data.health_band == HealthBand.ATTENTION:
        return MaintenancePriority.MEDIUM
    if data.health_band == HealthBand.WATCH:
        return MaintenancePriority.LOW
    if data.health_score is None:
        return MaintenancePriority.INSUFFICIENT_DATA
    return MaintenancePriority.NONE


def recommended_actions(
    priority: MaintenancePriority,
    *,
    has_concerning_sensor: bool,
) -> tuple[MaintenanceAction, ...]:
    by_priority = {
        MaintenancePriority.NONE: [MaintenanceAction.CONTINUE_MONITORING],
        MaintenancePriority.LOW: [
            MaintenanceAction.CONTINUE_MONITORING,
            MaintenanceAction.REVIEW_OPERATING_CONDITIONS,
        ],
        MaintenancePriority.MEDIUM: [
            MaintenanceAction.INSPECT_MACHINE,
            MaintenanceAction.SCHEDULE_MAINTENANCE_REVIEW,
        ],
        MaintenancePriority.HIGH: [
            MaintenanceAction.INSPECT_MACHINE,
            MaintenanceAction.SCHEDULE_MAINTENANCE_REVIEW,
        ],
        MaintenancePriority.CRITICAL: [
            MaintenanceAction.IMMEDIATE_OPERATIONAL_REVIEW,
            MaintenanceAction.INSPECT_MACHINE,
        ],
        MaintenancePriority.INSUFFICIENT_DATA: [MaintenanceAction.VERIFY_TELEMETRY],
    }
    actions = by_priority[priority]
    if has_concerning_sensor and priority not in {
        MaintenancePriority.NONE,
        MaintenancePriority.INSUFFICIENT_DATA,
    }:
        actions.append(MaintenanceAction.INSPECT_SENSOR_OR_COMPONENT)
    return tuple(dict.fromkeys(actions[:MAX_MAINTENANCE_ACTIONS]))
