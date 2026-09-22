from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.health_scoring import HealthBand, HealthConfidence
from app.domain.maintenance_intelligence import (
    MAINTENANCE_INTELLIGENCE_VERSION,
    MAX_MAINTENANCE_REASONS,
    MaintenanceEvidenceType,
    MaintenancePolicyInput,
    classify_maintenance_priority,
    recommended_actions,
)
from app.domain.predictive_features import PredictiveFeatureWindow
from app.models import Alert, AlertSeverity
from app.repositories.alert import AlertRepository
from app.schemas.health import MachineHealthScoreResponse, SensorHealthScoreResponse
from app.schemas.maintenance import (
    MachineMaintenanceAssessmentResponse,
    MaintenanceEvidenceResponse,
)
from app.services.health_scoring import HealthScoringService

MAINTENANCE_INDICATOR_TYPE = "DETERMINISTIC_MAINTENANCE_ASSESSMENT"


class MaintenanceIntelligenceService:
    def __init__(self, db: Session) -> None:
        self.health_service = HealthScoringService(db)
        self.alert_repository = AlertRepository(db)

    def get_machine_assessment(
        self,
        *,
        machine_id: UUID,
        window: PredictiveFeatureWindow = PredictiveFeatureWindow.TWENTY_FOUR_HOURS,
        end: datetime | None = None,
    ) -> MachineMaintenanceAssessmentResponse:
        health = self.health_service.get_machine_health_score(
            machine_id=machine_id, window=window, end=end
        )
        alerts = self.alert_repository.get_unresolved_alerts_for_machine(machine_id)
        critical_count = sum(alert.severity == AlertSeverity.CRITICAL for alert in alerts)
        warning_count = sum(alert.severity == AlertSeverity.WARNING for alert in alerts)
        concerning = next(
            (
                sensor
                for sensor in health.sensor_scores
                if sensor.sensor_id == health.most_concerning_sensor_id
            ),
            None,
        )
        priority = classify_maintenance_priority(
            MaintenancePolicyInput(
                health_score=health.health_score,
                health_band=health.health_band,
                confidence=health.confidence,
                alert_severities=tuple(alert.severity for alert in alerts),
                has_concerning_sensor=concerning is not None,
            )
        )
        evidence = self._evidence(health, alerts, concerning)
        reasons = self._reasons(
            health=health,
            critical_count=critical_count,
            warning_count=warning_count,
            concerning=concerning,
        )
        return MachineMaintenanceAssessmentResponse(
            indicator_type=MAINTENANCE_INDICATOR_TYPE,
            feature_version=health.feature_version,
            scoring_version=health.scoring_version,
            maintenance_policy_version=MAINTENANCE_INTELLIGENCE_VERSION,
            machine_id=health.machine_id,
            window=health.window,
            window_start=health.window_start,
            window_end=health.window_end,
            health_score=health.health_score,
            health_band=health.health_band,
            confidence=health.confidence,
            maintenance_priority=priority,
            unresolved_alert_count=len(alerts),
            critical_alert_count=critical_count,
            warning_alert_count=warning_count,
            most_concerning_sensor_id=health.most_concerning_sensor_id,
            most_concerning_sensor_name=(concerning.sensor_name if concerning else None),
            evidence=evidence,
            recommended_actions=list(
                recommended_actions(priority, has_concerning_sensor=concerning is not None)
            ),
            reasons=reasons[:MAX_MAINTENANCE_REASONS],
        )

    @staticmethod
    def _evidence(
        health: MachineHealthScoreResponse,
        alerts: list[Alert],
        concerning: SensorHealthScoreResponse | None,
    ) -> list[MaintenanceEvidenceResponse]:
        evidence = [
            MaintenanceEvidenceResponse(
                type=(
                    MaintenanceEvidenceType.CRITICAL_ALERT
                    if alert.severity == AlertSeverity.CRITICAL
                    else MaintenanceEvidenceType.WARNING_ALERT
                ),
                alert_id=alert.id,
                severity=alert.severity,
                message=alert.message,
            )
            for alert in alerts
        ]
        if health.health_band in {HealthBand.WATCH, HealthBand.ATTENTION}:
            evidence.append(
                MaintenanceEvidenceResponse(
                    type=MaintenanceEvidenceType.LOW_HEALTH_SCORE,
                    message=(
                        f"Maintenance health is {health.health_score:.1f} / 100 "
                        f"({health.health_band.value})."
                    ),
                )
            )
        if concerning is not None:
            evidence.append(
                MaintenanceEvidenceResponse(
                    type=MaintenanceEvidenceType.CONCERNING_SENSOR,
                    sensor_id=concerning.sensor_id,
                    sensor_name=concerning.sensor_name,
                    message=f"{concerning.sensor_name} has the lowest health score.",
                )
            )
            if concerning.component_penalties.exceedance > 0:
                evidence.append(
                    MaintenanceEvidenceResponse(
                        type=MaintenanceEvidenceType.THRESHOLD_EXCEEDANCE,
                        sensor_id=concerning.sensor_id,
                        sensor_name=concerning.sensor_name,
                        message=f"{concerning.sensor_name} recorded threshold exceedance.",
                    )
                )
        if health.health_score is None:
            evidence.append(
                MaintenanceEvidenceResponse(
                    type=MaintenanceEvidenceType.MISSING_TELEMETRY,
                    message="Telemetry is insufficient for a maintenance health score.",
                )
            )
        elif health.confidence != HealthConfidence.HIGH:
            evidence.append(
                MaintenanceEvidenceResponse(
                    type=MaintenanceEvidenceType.LOW_CONFIDENCE,
                    message=f"Telemetry confidence is {health.confidence.value.lower()}.",
                )
            )
        return evidence

    @staticmethod
    def _reasons(
        *,
        health: MachineHealthScoreResponse,
        critical_count: int,
        warning_count: int,
        concerning: SensorHealthScoreResponse | None,
    ) -> list[str]:
        reasons: list[str] = []
        if critical_count:
            critical_verb = "require" if critical_count != 1 else "requires"
            critical_label = "alerts" if critical_count != 1 else "alert"
            reasons.append(
                f"{critical_count} unresolved critical {critical_label} {critical_verb} "
                "immediate operational review."
            )
        if warning_count:
            warning_verb = "require" if warning_count != 1 else "requires"
            warning_label = "alerts" if warning_count != 1 else "alert"
            reasons.append(
                f"{warning_count} unresolved warning {warning_label} {warning_verb} "
                "operating-condition review."
            )
        if health.health_score is None:
            reasons.append("Telemetry coverage is insufficient for a health score.")
        else:
            reasons.append(
                f"Machine health score is {health.health_score:.1f} / 100 "
                f"({health.health_band.value})."
            )
        if concerning is not None:
            reasons.append(
                f"{concerning.sensor_name} has the lowest health score at "
                f"{concerning.health_score:.1f} / 100."
            )
        reasons.append(
            f"Telemetry confidence is {health.confidence.value.lower()}; confidence describes "
            "coverage, not machine condition."
        )
        return reasons
