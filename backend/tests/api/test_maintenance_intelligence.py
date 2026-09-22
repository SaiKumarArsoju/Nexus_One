from datetime import UTC, datetime, timedelta
from math import isfinite
from uuid import UUID

import pytest
from app.core.enums import SensorType
from app.models import Alert, AlertSeverity, AlertStatus, AlertThreshold, Sensor, SensorReading

ASSESSMENT_END = datetime(2026, 8, 28, 12, tzinfo=UTC)


def _sensor(db, machine, *, name="Temperature Sensor"):
    sensor = Sensor(
        machine_id=machine.id,
        name=name,
        sensor_type=SensorType.TEMPERATURE,
        unit="°C",
    )
    db.add(sensor)
    db.flush()
    return sensor


def _readings(db, sensor, values):
    for index, value in enumerate(values, start=1):
        db.add(
            SensorReading(
                sensor_id=sensor.id,
                value=value,
                recorded_at=ASSESSMENT_END - timedelta(minutes=len(values) - index + 1),
            )
        )
    db.flush()


def _alert(db, machine, severity, status=AlertStatus.ACTIVE, *, message="Condition detected"):
    alert = Alert(
        machine_id=machine.id,
        severity=severity,
        status=status,
        alert_type=f"{severity.value}_{status.value}_{UUID(int=len(db.new) + 1)}",
        message=message,
    )
    db.add(alert)
    db.flush()
    return alert


def _query(client, machine, **params):
    return client.get(
        f"/api/v1/machines/{machine.id}/maintenance-assessment",
        params={"end": ASSESSMENT_END.isoformat(), **params},
    )


def test_healthy_machine_without_alerts_has_no_priority(client, db, test_machine):
    sensor = _sensor(db, test_machine)
    _readings(db, sensor, [50] * 5)

    payload = _query(client, test_machine).json()

    assert payload["maintenance_priority"] == "NONE"
    assert payload["recommended_actions"] == ["CONTINUE_MONITORING"]
    assert payload["maintenance_policy_version"] == "v1"
    assert payload["feature_version"] == payload["scoring_version"] == "v1"
    assert payload["indicator_type"] == "DETERMINISTIC_MAINTENANCE_ASSESSMENT"


@pytest.mark.parametrize(
    ("values", "severity", "expected_band", "expected_priority", "expected_confidence"),
    [
        ([90, 90, 90, 90, 91], None, "WATCH", "LOW", "HIGH"),
        ([120] * 5, None, "ATTENTION", "MEDIUM", "HIGH"),
        ([120] * 5, AlertSeverity.WARNING, "ATTENTION", "HIGH", "HIGH"),
        ([120], None, "ATTENTION", "MEDIUM", "LOW"),
    ],
    ids=["watch", "attention", "attention-warning", "sparse-concerning"],
)
def test_health_and_warning_policy_fixtures(
    client,
    db,
    test_machine,
    values,
    severity,
    expected_band,
    expected_priority,
    expected_confidence,
):
    sensor = _sensor(db, test_machine)
    _readings(db, sensor, values)
    if severity is not None:
        _alert(db, test_machine, severity)

    payload = _query(client, test_machine).json()

    assert payload["health_band"] == expected_band
    assert payload["maintenance_priority"] == expected_priority
    assert payload["confidence"] == expected_confidence
    assert payload["most_concerning_sensor_id"] == str(sensor.id)
    assert payload["most_concerning_sensor_name"] == sensor.name


@pytest.mark.parametrize(
    ("severity", "status", "expected"),
    [
        (AlertSeverity.WARNING, AlertStatus.ACTIVE, "MEDIUM"),
        (AlertSeverity.CRITICAL, AlertStatus.ACTIVE, "CRITICAL"),
        (AlertSeverity.CRITICAL, AlertStatus.ACKNOWLEDGED, "CRITICAL"),
        (AlertSeverity.CRITICAL, AlertStatus.RESOLVED, "NONE"),
    ],
)
def test_alert_status_and_severity_drive_current_priority(
    client, db, test_machine, severity, status, expected
):
    sensor = _sensor(db, test_machine)
    _readings(db, sensor, [50] * 5)
    _alert(db, test_machine, severity, status)

    payload = _query(client, test_machine).json()

    assert payload["maintenance_priority"] == expected
    assert payload["unresolved_alert_count"] == (0 if status == AlertStatus.RESOLVED else 1)


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (None, "INSUFFICIENT_DATA"),
        (AlertSeverity.WARNING, "MEDIUM"),
        (AlertSeverity.CRITICAL, "CRITICAL"),
    ],
)
def test_no_data_priority_respects_operational_alert_evidence(
    client, db, test_machine, severity, expected
):
    _sensor(db, test_machine)
    if severity is not None:
        _alert(db, test_machine, severity)

    payload = _query(client, test_machine).json()

    assert payload["health_score"] is None
    assert payload["confidence"] == "NONE"
    assert payload["maintenance_priority"] == expected


def test_multiple_alerts_have_deterministic_counts_evidence_and_actions(client, db, test_machine):
    sensor = _sensor(db, test_machine)
    _readings(db, sensor, [120] * 5)
    _alert(db, test_machine, AlertSeverity.WARNING, message="Warning one")
    _alert(db, test_machine, AlertSeverity.WARNING, message="Warning two")
    _alert(db, test_machine, AlertSeverity.CRITICAL, message="Critical one")

    first = _query(client, test_machine).json()
    second = _query(client, test_machine).json()

    assert first == second
    assert first["maintenance_priority"] == "CRITICAL"
    assert first["critical_alert_count"] == 1
    assert first["warning_alert_count"] == 2
    assert [item["type"] for item in first["evidence"][:3]] == [
        "CRITICAL_ALERT",
        "WARNING_ALERT",
        "WARNING_ALERT",
    ]
    assert len(first["recommended_actions"]) == len(set(first["recommended_actions"])) <= 3
    assert len(first["reasons"]) <= 5


def test_multiple_same_type_sensors_reuse_health_services_most_concerning_sensor(
    client, db, test_machine
):
    healthy = _sensor(db, test_machine, name="Healthy Temperature")
    concerning = _sensor(db, test_machine, name="Concerning Temperature")
    _readings(db, healthy, [50] * 5)
    _readings(db, concerning, [120] * 5)

    payload = _query(client, test_machine).json()

    assert payload["most_concerning_sensor_id"] == str(concerning.id)
    assert payload["most_concerning_sensor_name"] == concerning.name
    assert payload["maintenance_priority"] == "MEDIUM"


@pytest.mark.parametrize(
    ("window", "expected_start"),
    [
        ("1h", "2026-08-28T11:00:00Z"),
        ("6h", "2026-08-28T06:00:00Z"),
        ("24h", "2026-08-27T12:00:00Z"),
        ("7d", "2026-08-21T12:00:00Z"),
    ],
)
def test_supported_windows_return_exact_bounds(client, test_machine, window, expected_start):
    payload = _query(client, test_machine, window=window).json()

    assert payload["window"] == window
    assert payload["window_start"] == expected_start
    assert payload["window_end"] == "2026-08-28T12:00:00Z"


def test_default_and_omitted_end_behavior(client, test_machine):
    default_payload = _query(client, test_machine).json()
    before = datetime.now(UTC)
    current = client.get(f"/api/v1/machines/{test_machine.id}/maintenance-assessment")
    after = datetime.now(UTC)

    assert default_payload["window"] == "24h"
    current_end = datetime.fromisoformat(current.json()["window_end"].replace("Z", "+00:00"))
    assert before <= current_end <= after


@pytest.mark.parametrize("params", [{"end": "2026-08-28T12:00:00"}, {"window": "30d"}])
def test_invalid_query_returns_422(client, test_machine, params):
    response = client.get(
        f"/api/v1/machines/{test_machine.id}/maintenance-assessment", params=params
    )
    assert response.status_code == 422


def test_unknown_machine_returns_404(client):
    response = client.get(f"/api/v1/machines/{UUID(int=0)}/maintenance-assessment")
    assert response.status_code == 404
    assert response.json() == {"detail": "Machine not found"}


def test_missing_threshold_returns_500(client, db, test_machine):
    _sensor(db, test_machine)
    db.delete(db.get(AlertThreshold, SensorType.TEMPERATURE))
    db.flush()

    response = _query(client, test_machine)
    assert response.status_code == 500


def test_contract_is_finite_and_contains_no_prediction_claims(client, db, test_machine):
    sensor = _sensor(db, test_machine)
    _readings(db, sensor, [50, 60, 70, 80, 90])
    payload = _query(client, test_machine).json()

    def assert_finite(value):
        if isinstance(value, float):
            assert isfinite(value)
        elif isinstance(value, dict):
            for item in value.values():
                assert_finite(item)
        elif isinstance(value, list):
            for item in value:
                assert_finite(item)

    assert_finite(payload)
    serialized = str(payload).lower()
    forbidden = ["probability", "remaining_useful_life", "diagnosis"]
    assert all(word not in serialized for word in forbidden)
