from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.alert_rules import (
    ALERT_RULES,
    ALERT_RULES_BY_SENSOR_TYPE,
    AlertThresholdConfigurationError,
    validate_threshold_map,
)
from app.models import AlertThreshold
from app.repositories import AlertThresholdRepository
from app.schemas import AlertThresholdResponse


class AlertThresholdService:
    def __init__(self, db: Session) -> None:
        self.repository = AlertThresholdRepository(db)

    def get_alert_thresholds(self) -> list[AlertThresholdResponse]:
        thresholds = {threshold.sensor_type: threshold for threshold in self.repository.get_all()}
        validate_threshold_map(
            {
                sensor_type: threshold.threshold_value
                for sensor_type, threshold in thresholds.items()
            }
        )

        return [self._to_response(thresholds[rule.sensor_type]) for rule in ALERT_RULES]

    def update_alert_threshold(
        self,
        sensor_type: SensorType,
        threshold_value: float,
    ) -> AlertThresholdResponse:
        threshold = self.repository.update_threshold(
            sensor_type=sensor_type,
            threshold_value=threshold_value,
        )

        if threshold is None:
            raise AlertThresholdConfigurationError(
                f"Missing persisted alert threshold for: {sensor_type.value}"
            )

        return self._to_response(threshold)

    @staticmethod
    def _to_response(
        threshold: AlertThreshold,
    ) -> AlertThresholdResponse:
        rule = ALERT_RULES_BY_SENSOR_TYPE[threshold.sensor_type]

        return AlertThresholdResponse(
            sensor_type=threshold.sensor_type,
            threshold_value=threshold.threshold_value,
            unit=rule.unit,
            severity=rule.severity,
            alert_type=rule.alert_type,
            updated_at=threshold.updated_at,
        )
