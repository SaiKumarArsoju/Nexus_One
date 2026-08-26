from app.core.enums import SensorType
from app.domain.alert_rules import ALERT_RULES_BY_SENSOR_TYPE

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
