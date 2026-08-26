from sqlalchemy.orm import Session

from app.domain.alert_rules import ALERT_RULES
from app.repositories import AlertThresholdRepository
from app.schemas import AlertThresholdResponse


class AlertThresholdService:
    def __init__(self, db: Session) -> None:
        self.repository = AlertThresholdRepository(db)

    def get_alert_thresholds(self) -> list[AlertThresholdResponse]:
        thresholds = {threshold.sensor_type: threshold for threshold in self.repository.get_all()}

        responses: list[AlertThresholdResponse] = []

        for rule in ALERT_RULES:
            threshold = thresholds.get(rule.sensor_type)

            if threshold is None:
                raise RuntimeError(f"Missing alert threshold for {rule.sensor_type.value}")

            responses.append(
                AlertThresholdResponse(
                    sensor_type=rule.sensor_type,
                    threshold_value=threshold.threshold_value,
                    unit=rule.unit,
                    severity=rule.severity,
                    alert_type=rule.alert_type,
                    updated_at=threshold.updated_at,
                )
            )

        return responses
