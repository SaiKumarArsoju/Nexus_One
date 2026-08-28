from uuid import uuid4

from app.core.enums import MachineStatus, SensorType
from app.models import Alert, AlertThreshold, Machine, Sensor, SensorReading
from sqlalchemy import func, select


def _count(db, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _create_sensor(
    db,
    machine: Machine,
    *,
    name: str,
    sensor_type: SensorType,
    unit: str,
) -> Sensor:
    sensor = Sensor(
        name=name,
        sensor_type=sensor_type,
        unit=unit,
        machine_id=machine.id,
    )
    db.add(sensor)
    db.flush()
    return sensor


def test_get_sensors_returns_empty_collection(client):
    response = client.get("/api/v1/sensors")

    assert response.status_code == 200
    assert response.json() == []


def test_get_sensors_returns_required_discovery_fields(client, db, test_machine):
    sensor = _create_sensor(
        db,
        test_machine,
        name="Temperature Sensor",
        sensor_type=SensorType.TEMPERATURE,
        unit="C",
    )

    response = client.get("/api/v1/sensors")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(sensor.id),
            "name": "Temperature Sensor",
            "sensor_type": "TEMPERATURE",
            "unit": "C",
            "machine_id": str(test_machine.id),
        }
    ]


def test_get_sensors_serializes_multiple_sensor_types(client, db, test_machine):
    for sensor_type, unit in (
        (SensorType.TEMPERATURE, "C"),
        (SensorType.PRESSURE, "bar"),
        (SensorType.VIBRATION, "mm/s"),
        (SensorType.RPM, "rpm"),
        (SensorType.ENERGY, "kWh"),
    ):
        _create_sensor(
            db,
            test_machine,
            name=f"{sensor_type.value} Sensor",
            sensor_type=sensor_type,
            unit=unit,
        )

    response = client.get("/api/v1/sensors")

    assert response.status_code == 200
    assert [item["sensor_type"] for item in response.json()] == [
        sensor_type.value for sensor_type in SensorType
    ]


def test_get_sensors_returns_correct_machine_relationships(
    client,
    db,
    test_machine,
    test_production_line,
):
    second_machine = Machine(
        name="Second Test Machine",
        serial_number=f"TEST-{uuid4()}",
        manufacturer="NEXUS Test",
        model_number="TEST-002",
        status=MachineStatus.RUNNING,
        production_line_id=test_production_line.id,
    )
    db.add(second_machine)
    db.flush()

    first_sensor = _create_sensor(
        db,
        test_machine,
        name="First Machine Sensor",
        sensor_type=SensorType.TEMPERATURE,
        unit="C",
    )
    second_sensor = _create_sensor(
        db,
        second_machine,
        name="Second Machine Sensor",
        sensor_type=SensorType.PRESSURE,
        unit="bar",
    )

    response = client.get("/api/v1/sensors")

    assert response.status_code == 200
    machine_ids_by_sensor = {item["id"]: item["machine_id"] for item in response.json()}
    assert machine_ids_by_sensor == {
        str(first_sensor.id): str(test_machine.id),
        str(second_sensor.id): str(second_machine.id),
    }


def test_get_sensors_uses_deterministic_ordering(client, db, test_machine):
    sensors = [
        _create_sensor(
            db,
            test_machine,
            name="Zulu Temperature Sensor",
            sensor_type=SensorType.TEMPERATURE,
            unit="C",
        ),
        _create_sensor(
            db,
            test_machine,
            name="Alpha Pressure Sensor",
            sensor_type=SensorType.PRESSURE,
            unit="bar",
        ),
        _create_sensor(
            db,
            test_machine,
            name="Alpha Temperature Sensor",
            sensor_type=SensorType.TEMPERATURE,
            unit="C",
        ),
    ]

    first_response = client.get("/api/v1/sensors")
    second_response = client.get("/api/v1/sensors")

    assert first_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert [item["id"] for item in first_response.json()] == [
        str(sensors[2].id),
        str(sensors[0].id),
        str(sensors[1].id),
    ]


def test_get_sensors_has_no_side_effects(client, db, test_machine):
    _create_sensor(
        db,
        test_machine,
        name="Read Only Sensor",
        sensor_type=SensorType.ENERGY,
        unit="kWh",
    )
    sensor_count = _count(db, Sensor)
    reading_count = _count(db, SensorReading)
    alert_count = _count(db, Alert)
    threshold_snapshot = list(
        db.execute(
            select(
                AlertThreshold.sensor_type,
                AlertThreshold.threshold_value,
                AlertThreshold.updated_at,
            ).order_by(AlertThreshold.sensor_type)
        ).all()
    )

    response = client.get("/api/v1/sensors")

    assert response.status_code == 200
    assert _count(db, Sensor) == sensor_count
    assert _count(db, SensorReading) == reading_count
    assert _count(db, Alert) == alert_count
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
        == threshold_snapshot
    )
