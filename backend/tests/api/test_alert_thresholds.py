import pytest
from app.core.enums import SensorType
from app.domain.alert_rules import ALERT_RULES_BY_SENSOR_TYPE
from app.models import Alert, AlertThreshold, Sensor, SensorReading
from sqlalchemy import select

EXPECTED_THRESHOLDS = {
    SensorType.TEMPERATURE: 90.0,
    SensorType.PRESSURE: 7.5,
    SensorType.VIBRATION: 0.4,
    SensorType.RPM: 2800.0,
    SensorType.ENERGY: 28.0,
}


def test_get_alert_thresholds_returns_all_defaults_in_sensor_type_order(client):
    response = client.get("/api/v1/alert-thresholds")

    assert response.status_code == 200

    thresholds = response.json()

    assert len(thresholds) == 5
    assert [item["sensor_type"] for item in thresholds] == [
        sensor_type.value for sensor_type in SensorType
    ]
    assert {
        SensorType(item["sensor_type"]): item["threshold_value"] for item in thresholds
    } == EXPECTED_THRESHOLDS
    assert all(item["threshold_value"] > 0 for item in thresholds)


def test_get_alert_thresholds_includes_rule_catalog_metadata(client):
    response = client.get("/api/v1/alert-thresholds")

    assert response.status_code == 200

    for item in response.json():
        rule = ALERT_RULES_BY_SENSOR_TYPE[SensorType(item["sensor_type"])]

        assert set(item) == {
            "sensor_type",
            "threshold_value",
            "unit",
            "severity",
            "alert_type",
            "updated_at",
        }
        assert item["unit"] == rule.unit
        assert item["severity"] == rule.severity.value
        assert item["alert_type"] == rule.alert_type
        assert item["updated_at"] is not None


def test_update_temperature_threshold_returns_rich_response_and_updates_get(
    client,
):
    initial_thresholds = {
        item["sensor_type"]: item for item in client.get("/api/v1/alert-thresholds").json()
    }

    response = client.put(
        "/api/v1/alert-thresholds/TEMPERATURE",
        json={"threshold_value": 95.0},
    )

    assert response.status_code == 200

    updated = response.json()
    rule = ALERT_RULES_BY_SENSOR_TYPE[SensorType.TEMPERATURE]

    assert set(updated) == {
        "sensor_type",
        "threshold_value",
        "unit",
        "severity",
        "alert_type",
        "updated_at",
    }
    assert updated["sensor_type"] == SensorType.TEMPERATURE.value
    assert updated["threshold_value"] == 95.0
    assert updated["unit"] == rule.unit
    assert updated["severity"] == rule.severity.value
    assert updated["alert_type"] == rule.alert_type
    assert updated["updated_at"] != initial_thresholds[SensorType.TEMPERATURE.value]["updated_at"]

    thresholds_after_update = {
        item["sensor_type"]: item["threshold_value"]
        for item in client.get("/api/v1/alert-thresholds").json()
    }

    assert thresholds_after_update == {
        **{sensor_type.value: threshold for sensor_type, threshold in EXPECTED_THRESHOLDS.items()},
        SensorType.TEMPERATURE.value: 95.0,
    }


@pytest.mark.parametrize(
    "threshold_value",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="positive-infinity"),
        pytest.param("-Infinity", id="negative-infinity"),
    ],
)
def test_update_threshold_rejects_non_positive_or_non_finite_values(
    client,
    threshold_value,
):
    response = client.put(
        "/api/v1/alert-thresholds/TEMPERATURE",
        json={"threshold_value": threshold_value},
    )

    assert response.status_code == 422


def test_update_threshold_rejects_invalid_sensor_type(client):
    response = client.put(
        "/api/v1/alert-thresholds/NOT_A_SENSOR",
        json={"threshold_value": 95.0},
    )

    assert response.status_code == 422


def test_update_missing_threshold_returns_configuration_error_without_creating_row(
    client,
    db,
):
    threshold = db.get(AlertThreshold, SensorType.ENERGY)

    assert threshold is not None

    db.delete(threshold)
    db.flush()

    response = client.put(
        "/api/v1/alert-thresholds/ENERGY",
        json={"threshold_value": 30.0},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Missing persisted alert threshold for: ENERGY"}
    assert db.get(AlertThreshold, SensorType.ENERGY) is None


def test_threshold_api_update_propagates_to_subsequent_alert_sync(
    client,
    db,
    test_machine,
):
    update_response = client.put(
        "/api/v1/alert-thresholds/TEMPERATURE",
        json={"threshold_value": 70.0},
    )
    assert update_response.status_code == 200

    sensor = Sensor(
        name="Threshold API Temperature Sensor",
        sensor_type=SensorType.TEMPERATURE,
        unit="°C",
        machine_id=test_machine.id,
    )
    db.add(sensor)
    db.flush()

    db.add(
        SensorReading(
            sensor_id=sensor.id,
            value=80.0,
        )
    )
    db.flush()

    sync_response = client.post("/api/v1/alerts/sync")

    assert sync_response.status_code == 200
    assert sync_response.json() == {"created_alerts": 1}
    assert (
        db.scalar(
            select(Alert).where(
                Alert.machine_id == test_machine.id,
                Alert.alert_type == "HIGH_TEMPERATURE",
            )
        )
        is not None
    )
