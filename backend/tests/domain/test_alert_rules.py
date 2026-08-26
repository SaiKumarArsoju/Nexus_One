from app.core.enums import SensorType
from app.domain.alert_rules import ALERT_RULES, ALERT_RULES_BY_SENSOR_TYPE
from app.models import AlertSeverity

EXPECTED_RULE_METADATA = {
    SensorType.TEMPERATURE: (
        "HIGH_TEMPERATURE",
        AlertSeverity.WARNING,
        "High temperature detected",
        20,
        "°C",
    ),
    SensorType.PRESSURE: (
        "HIGH_PRESSURE",
        AlertSeverity.WARNING,
        "High pressure detected",
        15,
        "bar",
    ),
    SensorType.VIBRATION: (
        "HIGH_VIBRATION",
        AlertSeverity.CRITICAL,
        "High vibration detected",
        25,
        "mm/s",
    ),
    SensorType.RPM: (
        "HIGH_RPM",
        AlertSeverity.WARNING,
        "High RPM detected",
        15,
        "rpm",
    ),
    SensorType.ENERGY: (
        "HIGH_ENERGY",
        AlertSeverity.WARNING,
        "High energy consumption detected",
        10,
        "kWh",
    ),
}


def test_alert_rule_catalog_covers_every_sensor_type_in_order():
    assert tuple(rule.sensor_type for rule in ALERT_RULES) == tuple(SensorType)
    assert set(ALERT_RULES_BY_SENSOR_TYPE) == set(SensorType)


def test_alert_rule_catalog_preserves_existing_metadata():
    assert {
        rule.sensor_type: (
            rule.alert_type,
            rule.severity,
            rule.message,
            rule.health_score_penalty,
            rule.unit,
        )
        for rule in ALERT_RULES
    } == EXPECTED_RULE_METADATA


def test_alert_rules_use_strict_greater_than_comparison():
    for rule in ALERT_RULES:
        assert rule.is_abnormal(10.01, 10.0)
        assert not rule.is_abnormal(10.0, 10.0)
        assert not rule.is_abnormal(9.99, 10.0)
