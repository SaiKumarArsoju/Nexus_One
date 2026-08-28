from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.core.enums import SensorType
from app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertThreshold,
    Sensor,
    SensorReading,
)
from sqlalchemy import func, select


@pytest.fixture
def test_sensor(db, test_machine) -> Sensor:
    sensor = Sensor(
        name="Telemetry Ingestion Temperature Sensor",
        sensor_type=SensorType.TEMPERATURE,
        unit="°C",
        machine_id=test_machine.id,
    )

    db.add(sensor)
    db.flush()

    return sensor


def _reading_count(db) -> int:
    return db.scalar(select(func.count()).select_from(SensorReading)) or 0


def _alert_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Alert)) or 0


def _temperature_alerts(db, test_sensor) -> list[Alert]:
    return list(
        db.scalars(
            select(Alert)
            .where(
                Alert.machine_id == test_sensor.machine_id,
                Alert.alert_type == "HIGH_TEMPERATURE",
            )
            .order_by(Alert.created_at)
        )
    )


def _ingest_temperature(
    client,
    test_sensor,
    value: float,
):
    return client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(test_sensor.id),
            "value": value,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )


def test_ingest_telemetry_reading_persists_existing_sensor_reading(
    client,
    db,
    test_sensor,
):
    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(test_sensor.id),
            "value": 72.5,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )

    assert response.status_code == 201

    persisted = response.json()

    assert set(persisted) == {
        "id",
        "sensor_id",
        "value",
        "recorded_at",
    }
    assert persisted["sensor_id"] == str(test_sensor.id)
    assert persisted["value"] == 72.5
    assert datetime.fromisoformat(persisted["recorded_at"].replace("Z", "+00:00")) == datetime(
        2026, 8, 28, 1, 30, tzinfo=UTC
    )

    reading = db.get(SensorReading, UUID(persisted["id"]))

    assert reading is not None
    assert reading.sensor_id == test_sensor.id
    assert reading.value == 72.5
    assert reading.recorded_at == datetime(
        2026,
        8,
        28,
        1,
        30,
        tzinfo=UTC,
    )
    assert _temperature_alerts(db, test_sensor) == []


def test_ingest_telemetry_reading_rejects_unknown_sensor(
    client,
    db,
):
    initial_count = _reading_count(db)
    initial_alert_count = _alert_count(db)

    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(uuid4()),
            "value": 72.5,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Sensor not found"}
    assert _reading_count(db) == initial_count
    assert _alert_count(db) == initial_alert_count


def test_ingest_telemetry_reading_rejects_invalid_sensor_uuid(
    client,
    db,
):
    initial_reading_count = _reading_count(db)
    initial_alert_count = _alert_count(db)

    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": "not-a-uuid",
            "value": 72.5,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )

    assert response.status_code == 422
    assert _reading_count(db) == initial_reading_count
    assert _alert_count(db) == initial_alert_count


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="positive-infinity"),
        pytest.param("-Infinity", id="negative-infinity"),
    ],
)
def test_ingest_telemetry_reading_rejects_non_finite_value(
    client,
    test_sensor,
    value,
):
    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(test_sensor.id),
            "value": value,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )

    assert response.status_code == 422


def test_ingest_telemetry_reading_rejects_timezone_naive_timestamp(
    client,
    test_sensor,
):
    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(test_sensor.id),
            "value": 72.5,
            "recorded_at": "2026-08-28T01:30:00",
        },
    )

    assert response.status_code == 422


def test_abnormal_telemetry_creates_active_alert_with_catalog_metadata(
    client,
    db,
    test_sensor,
):
    thresholds_before = list(
        db.execute(
            select(
                AlertThreshold.sensor_type,
                AlertThreshold.threshold_value,
                AlertThreshold.updated_at,
            ).order_by(AlertThreshold.sensor_type)
        ).all()
    )
    alert_count_before = _alert_count(db)

    response = _ingest_temperature(client, test_sensor, 1000.0)

    assert response.status_code == 201
    assert _alert_count(db) == alert_count_before + 1

    alert = _temperature_alerts(db, test_sensor)[0]

    assert alert.machine_id == test_sensor.machine_id
    assert alert.alert_type == "HIGH_TEMPERATURE"
    assert alert.severity == AlertSeverity.WARNING
    assert alert.status == AlertStatus.ACTIVE
    assert alert.message == "High temperature detected"
    assert (
        list(
            db.execute(
                select(
                    AlertThreshold.sensor_type,
                    AlertThreshold.threshold_value,
                    AlertThreshold.updated_at,
                ).order_by(AlertThreshold.sensor_type)
            ).all()
        )
        == thresholds_before
    )


def test_second_abnormal_reading_does_not_duplicate_open_alert(
    client,
    db,
    test_sensor,
):
    assert _ingest_temperature(client, test_sensor, 100.0).status_code == 201
    assert _ingest_temperature(client, test_sensor, 101.0).status_code == 201

    alerts = _temperature_alerts(db, test_sensor)

    assert len(alerts) == 1
    assert alerts[0].status == AlertStatus.ACTIVE


def test_abnormal_reading_preserves_acknowledged_open_alert(
    client,
    db,
    test_sensor,
):
    assert _ingest_temperature(client, test_sensor, 100.0).status_code == 201

    alert = _temperature_alerts(db, test_sensor)[0]
    alert.status = AlertStatus.ACKNOWLEDGED
    db.flush()

    assert _ingest_temperature(client, test_sensor, 101.0).status_code == 201

    db.refresh(alert)
    assert len(_temperature_alerts(db, test_sensor)) == 1
    assert alert.status == AlertStatus.ACKNOWLEDGED


def test_normal_reading_resolves_active_alert(
    client,
    db,
    test_sensor,
):
    assert _ingest_temperature(client, test_sensor, 100.0).status_code == 201

    alert = _temperature_alerts(db, test_sensor)[0]

    assert _ingest_temperature(client, test_sensor, 80.0).status_code == 201

    db.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED


def test_normal_reading_resolves_acknowledged_alert(
    client,
    db,
    test_sensor,
):
    assert _ingest_temperature(client, test_sensor, 100.0).status_code == 201

    alert = _temperature_alerts(db, test_sensor)[0]
    alert.status = AlertStatus.ACKNOWLEDGED
    db.flush()

    assert _ingest_temperature(client, test_sensor, 80.0).status_code == 201

    db.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED


def test_threshold_equality_resolves_open_alert(
    client,
    db,
    test_sensor,
):
    assert _ingest_temperature(client, test_sensor, 100.0).status_code == 201

    alert = _temperature_alerts(db, test_sensor)[0]

    assert _ingest_temperature(client, test_sensor, 90.0).status_code == 201

    db.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED


def test_new_abnormal_reading_creates_new_alert_after_resolution(
    client,
    db,
    test_sensor,
):
    assert _ingest_temperature(client, test_sensor, 100.0).status_code == 201

    historical_alert = _temperature_alerts(db, test_sensor)[0]

    assert _ingest_temperature(client, test_sensor, 80.0).status_code == 201

    db.refresh(historical_alert)
    assert historical_alert.status == AlertStatus.RESOLVED

    assert _ingest_temperature(client, test_sensor, 101.0).status_code == 201

    alerts = _temperature_alerts(db, test_sensor)
    new_alert = next(alert for alert in alerts if alert.id != historical_alert.id)

    db.refresh(historical_alert)
    assert len(alerts) == 2
    assert historical_alert.status == AlertStatus.RESOLVED
    assert new_alert.status == AlertStatus.ACTIVE


def test_ingestion_uses_persisted_threshold_value(
    client,
    db,
    test_sensor,
):
    threshold = db.get(AlertThreshold, SensorType.TEMPERATURE)

    assert threshold is not None

    threshold.threshold_value = 110.0
    db.flush()

    response = _ingest_temperature(client, test_sensor, 100.0)

    assert response.status_code == 201
    assert _temperature_alerts(db, test_sensor) == []


def test_missing_threshold_rolls_back_reading_and_alert_evaluation(
    client,
    db,
    test_sensor,
):
    threshold = db.get(AlertThreshold, SensorType.TEMPERATURE)

    assert threshold is not None

    db.delete(threshold)
    db.flush()

    initial_reading_count = _reading_count(db)
    initial_alert_count = _alert_count(db)

    response = _ingest_temperature(client, test_sensor, 100.0)

    assert response.status_code == 500
    assert response.json() == {"detail": "Missing persisted alert threshold for: TEMPERATURE"}
    assert _reading_count(db) == initial_reading_count
    assert _alert_count(db) == initial_alert_count
