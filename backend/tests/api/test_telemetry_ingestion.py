from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.core.enums import SensorType
from app.models import (
    Alert,
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


def test_ingest_telemetry_reading_rejects_unknown_sensor(
    client,
    db,
):
    initial_count = _reading_count(db)

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


def test_ingest_telemetry_reading_rejects_invalid_sensor_uuid(
    client,
):
    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": "not-a-uuid",
            "value": 72.5,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )

    assert response.status_code == 422


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


def test_ingest_telemetry_does_not_evaluate_alerts_or_modify_thresholds(
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
    alert_count_before = db.scalar(select(func.count()).select_from(Alert)) or 0

    response = client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(test_sensor.id),
            "value": 1000.0,
            "recorded_at": "2026-08-28T01:30:00Z",
        },
    )

    assert response.status_code == 201
    assert (db.scalar(select(func.count()).select_from(Alert)) or 0) == alert_count_before
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
