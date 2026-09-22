from app.domain.health_scoring import HealthBand, HealthConfidence
from app.domain.maintenance_intelligence import (
    MAINTENANCE_INTELLIGENCE_VERSION,
    MAX_MAINTENANCE_ACTIONS,
    MaintenanceAction,
    MaintenancePolicyInput,
    MaintenancePriority,
    classify_maintenance_priority,
    recommended_actions,
)
from app.models import AlertSeverity


def _input(
    *,
    score=100,
    band=HealthBand.HEALTHY,
    confidence=HealthConfidence.HIGH,
    alerts=(),
    concerning=False,
):
    return MaintenancePolicyInput(score, band, confidence, alerts, concerning)


def test_policy_version_is_v1():
    assert MAINTENANCE_INTELLIGENCE_VERSION == "v1"


def test_health_only_priority_policy():
    assert classify_maintenance_priority(_input()) == MaintenancePriority.NONE
    assert (
        classify_maintenance_priority(_input(score=70, band=HealthBand.WATCH))
        == MaintenancePriority.LOW
    )
    assert (
        classify_maintenance_priority(_input(score=50, band=HealthBand.ATTENTION))
        == MaintenancePriority.MEDIUM
    )
    assert (
        classify_maintenance_priority(
            _input(score=None, band=HealthBand.INSUFFICIENT_DATA, confidence=HealthConfidence.NONE)
        )
        == MaintenancePriority.INSUFFICIENT_DATA
    )


def test_unresolved_alerts_elevate_priority_without_using_confidence_as_a_penalty():
    assert (
        classify_maintenance_priority(_input(alerts=(AlertSeverity.WARNING,)))
        == MaintenancePriority.MEDIUM
    )
    assert (
        classify_maintenance_priority(
            _input(score=50, band=HealthBand.ATTENTION, alerts=(AlertSeverity.WARNING,))
        )
        == MaintenancePriority.HIGH
    )
    assert (
        classify_maintenance_priority(
            _input(
                score=None,
                band=HealthBand.INSUFFICIENT_DATA,
                confidence=HealthConfidence.NONE,
                alerts=(AlertSeverity.CRITICAL,),
            )
        )
        == MaintenancePriority.CRITICAL
    )


def test_alert_and_health_worsening_never_lower_priority():
    ordered = {
        MaintenancePriority.INSUFFICIENT_DATA: 0,
        MaintenancePriority.NONE: 1,
        MaintenancePriority.LOW: 2,
        MaintenancePriority.MEDIUM: 3,
        MaintenancePriority.HIGH: 4,
        MaintenancePriority.CRITICAL: 5,
    }
    healthy = classify_maintenance_priority(_input())
    warning = classify_maintenance_priority(_input(alerts=(AlertSeverity.WARNING,)))
    critical = classify_maintenance_priority(_input(alerts=(AlertSeverity.CRITICAL,)))
    watch = classify_maintenance_priority(_input(score=70, band=HealthBand.WATCH))
    attention = classify_maintenance_priority(_input(score=50, band=HealthBand.ATTENTION))

    assert ordered[warning] >= ordered[healthy]
    assert ordered[critical] >= ordered[warning]
    assert ordered[watch] >= ordered[healthy]
    assert ordered[attention] >= ordered[watch]


def test_actions_are_controlled_deduplicated_and_bounded():
    actions = recommended_actions(MaintenancePriority.CRITICAL, has_concerning_sensor=True)

    assert actions == (
        MaintenanceAction.IMMEDIATE_OPERATIONAL_REVIEW,
        MaintenanceAction.INSPECT_MACHINE,
        MaintenanceAction.INSPECT_SENSOR_OR_COMPONENT,
    )
    assert len(actions) == len(set(actions)) <= MAX_MAINTENANCE_ACTIONS
    assert recommended_actions(
        MaintenancePriority.INSUFFICIENT_DATA, has_concerning_sensor=False
    ) == (MaintenanceAction.VERIFY_TELEMETRY,)
