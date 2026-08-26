import pytest
from app.core.enums import SensorType
from app.domain.alert_rules import AlertThresholdConfigurationError
from app.models import (
    Alert,
    AlertStatus,
    AlertThreshold,
    Sensor,
    SensorReading,
)
from app.services import AlertService
from sqlalchemy import select


def _set_threshold(
    db,
    sensor_type: SensorType,
    threshold_value: float,
) -> None:
    threshold = db.get(AlertThreshold, sensor_type)

    assert threshold is not None

    threshold.threshold_value = threshold_value
    db.flush()


def _add_reading(
    db,
    test_machine,
    sensor_type: SensorType,
    value: float,
) -> None:
    sensor = Sensor(
        name=f"Test {sensor_type.value} Sensor",
        sensor_type=sensor_type,
        unit="test-unit",
        machine_id=test_machine.id,
    )
    db.add(sensor)
    db.flush()

    db.add(
        SensorReading(
            sensor_id=sensor.id,
            value=value,
        )
    )
    db.flush()


def _get_temperature_alert(db, test_machine) -> Alert | None:
    return db.scalar(
        select(Alert).where(
            Alert.machine_id == test_machine.id,
            Alert.alert_type == "HIGH_TEMPERATURE",
        )
    )


def test_alert_sync_uses_lower_persisted_threshold_without_duplicates(
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 70.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 80.0)

    service = AlertService(db)

    assert service.sync_machine_alerts() == 1
    assert service.sync_machine_alerts() == 0

    alerts = list(
        db.scalars(
            select(Alert).where(
                Alert.machine_id == test_machine.id,
                Alert.alert_type == "HIGH_TEMPERATURE",
                Alert.status.in_(
                    [
                        AlertStatus.ACTIVE,
                        AlertStatus.ACKNOWLEDGED,
                    ]
                ),
            )
        )
    )

    assert len(alerts) == 1
    assert alerts[0].status == AlertStatus.ACTIVE


def test_higher_persisted_threshold_prevents_old_cutoff_alert(
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 100.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 95.0)

    assert AlertService(db).sync_machine_alerts() == 0
    assert _get_temperature_alert(db, test_machine) is None


def test_acknowledged_alert_resolves_when_persisted_threshold_makes_reading_normal(
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 50.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 60.0)

    service = AlertService(db)
    assert service.sync_machine_alerts() == 1

    alert = _get_temperature_alert(db, test_machine)
    assert alert is not None

    alert.status = AlertStatus.ACKNOWLEDGED
    _set_threshold(db, SensorType.TEMPERATURE, 70.0)

    assert service.sync_machine_alerts() == 0

    db.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED


def test_alert_sync_treats_threshold_equality_as_normal(
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 60.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 60.0)

    assert AlertService(db).sync_machine_alerts() == 0
    assert _get_temperature_alert(db, test_machine) is None


def test_machine_detail_warnings_use_persisted_threshold(
    client,
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 50.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 60.0)

    response = client.get(f"/api/v1/machines/{test_machine.id}")

    assert response.status_code == 200
    assert response.json()["warnings"] == ["High temperature detected"]


def test_machine_health_uses_persisted_threshold_and_catalog_penalty(
    client,
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 50.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 60.0)

    response = client.get(f"/api/v1/machines/{test_machine.id}/health")

    assert response.status_code == 200
    assert response.json()["overall_health"] == 80
    assert response.json()["status"] == "WARNING"
    assert response.json()["warnings"] == ["High temperature detected"]


def test_dashboard_health_counts_use_persisted_threshold(
    client,
    db,
    test_machine,
):
    _set_threshold(db, SensorType.TEMPERATURE, 50.0)
    _add_reading(db, test_machine, SensorType.TEMPERATURE, 60.0)

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert response.json()["healthy_machines"] == 0
    assert response.json()["warning_machines"] == 1
    assert response.json()["critical_machines"] == 0


def test_missing_persisted_threshold_fails_clearly(
    db,
):
    threshold = db.get(AlertThreshold, SensorType.ENERGY)

    assert threshold is not None

    db.delete(threshold)
    db.flush()

    with pytest.raises(
        AlertThresholdConfigurationError,
        match="Missing persisted alert thresholds for: ENERGY",
    ):
        AlertService(db).sync_machine_alerts()
