from dataclasses import dataclass

from app.core.enums import SensorType
from app.models.alert import AlertSeverity


@dataclass(frozen=True)
class AlertRule:
    sensor_type: SensorType
    alert_type: str
    severity: AlertSeverity
    message: str
    health_score_penalty: int
    unit: str

    @staticmethod
    def is_abnormal(reading: float, threshold: float) -> bool:
        return reading > threshold


ALERT_RULES: tuple[AlertRule, ...] = (
    AlertRule(
        sensor_type=SensorType.TEMPERATURE,
        alert_type="HIGH_TEMPERATURE",
        severity=AlertSeverity.WARNING,
        message="High temperature detected",
        health_score_penalty=20,
        unit="°C",
    ),
    AlertRule(
        sensor_type=SensorType.PRESSURE,
        alert_type="HIGH_PRESSURE",
        severity=AlertSeverity.WARNING,
        message="High pressure detected",
        health_score_penalty=15,
        unit="bar",
    ),
    AlertRule(
        sensor_type=SensorType.VIBRATION,
        alert_type="HIGH_VIBRATION",
        severity=AlertSeverity.CRITICAL,
        message="High vibration detected",
        health_score_penalty=25,
        unit="mm/s",
    ),
    AlertRule(
        sensor_type=SensorType.RPM,
        alert_type="HIGH_RPM",
        severity=AlertSeverity.WARNING,
        message="High RPM detected",
        health_score_penalty=15,
        unit="rpm",
    ),
    AlertRule(
        sensor_type=SensorType.ENERGY,
        alert_type="HIGH_ENERGY",
        severity=AlertSeverity.WARNING,
        message="High energy consumption detected",
        health_score_penalty=10,
        unit="kWh",
    ),
)

ALERT_RULES_BY_SENSOR_TYPE: dict[SensorType, AlertRule] = {
    rule.sensor_type: rule for rule in ALERT_RULES
}
