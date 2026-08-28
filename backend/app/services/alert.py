from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.alert_rules import (
    ALERT_RULES,
    ALERT_RULES_BY_SENSOR_TYPE,
    AlertRule,
    AlertThresholdConfigurationError,
    validate_threshold_map,
)
from app.models import AlertStatus
from app.repositories import (
    AlertRepository,
    AlertThresholdRepository,
    MachineRepository,
)
from app.schemas import AlertResponse


class AlertService:
    def __init__(self, db: Session) -> None:
        self.repository = AlertRepository(db)
        self.machine_repository = MachineRepository(db)
        self.threshold_repository = AlertThresholdRepository(db)

    def get_active_alerts(self) -> list[AlertResponse]:
        rows = self.repository.get_active_alerts()

        return [
            AlertResponse(
                id=row.id,
                machine_id=row.machine_id,
                machine_name=row.machine_name,
                severity=row.severity.value,
                status=row.status.value,
                alert_type=row.alert_type,
                message=row.message,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get_alert_history(self) -> list[AlertResponse]:
        rows = self.repository.get_alert_history()

        return [
            AlertResponse(
                id=row.id,
                machine_id=row.machine_id,
                machine_name=row.machine_name,
                severity=row.severity.value,
                status=row.status.value,
                alert_type=row.alert_type,
                message=row.message,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def acknowledge_alert(
        self,
        alert_id: UUID,
    ) -> AlertResponse:
        alert = self.repository.get_alert_by_id(alert_id)

        if alert is None:
            raise LookupError("Alert not found")

        if alert.status == AlertStatus.RESOLVED:
            raise ValueError("Resolved alerts cannot be acknowledged")

        if alert.status == AlertStatus.ACTIVE:
            alert = self.repository.acknowledge_alert(alert)

        return AlertResponse(
            id=alert.id,
            machine_id=alert.machine_id,
            machine_name=alert.machine.name,
            severity=alert.severity.value,
            status=alert.status.value,
            alert_type=alert.alert_type,
            message=alert.message,
            created_at=alert.created_at,
        )

    def resolve_alert(
        self,
        alert_id: UUID,
    ) -> AlertResponse:
        alert = self.repository.get_alert_by_id(alert_id)

        if alert is None:
            raise LookupError("Alert not found")

        if alert.status != AlertStatus.RESOLVED:
            alert = self.repository.resolve_alert(alert)

        return AlertResponse(
            id=alert.id,
            machine_id=alert.machine_id,
            machine_name=alert.machine.name,
            severity=alert.severity.value,
            status=alert.status.value,
            alert_type=alert.alert_type,
            message=alert.message,
            created_at=alert.created_at,
        )

    def sync_machine_alerts(self) -> int:
        thresholds = self.threshold_repository.get_threshold_map()
        validate_threshold_map(thresholds)
        latest_readings = self.machine_repository.get_latest_sensor_readings()

        machine_values: dict = {}

        for reading in latest_readings:
            machine_values.setdefault(reading.machine_id, {})
            machine_values[reading.machine_id][reading.sensor_type] = reading.value

        created_count = 0

        for machine_id, values in machine_values.items():
            for rule in ALERT_RULES:
                created_count += self._apply_alert_rule(
                    machine_id=machine_id,
                    rule=rule,
                    value=values.get(rule.sensor_type),
                    threshold=thresholds[rule.sensor_type],
                )

        return created_count

    def evaluate_sensor_reading(
        self,
        machine_id: UUID,
        sensor_type: SensorType,
        value: float,
        *,
        commit: bool = True,
    ) -> bool:
        threshold = self.threshold_repository.get_by_sensor_type(sensor_type)

        if threshold is None:
            raise AlertThresholdConfigurationError(
                f"Missing persisted alert threshold for: {sensor_type.value}"
            )

        return bool(
            self._apply_alert_rule(
                machine_id=machine_id,
                rule=ALERT_RULES_BY_SENSOR_TYPE[sensor_type],
                value=value,
                threshold=threshold.threshold_value,
                commit=commit,
            )
        )

    def _apply_alert_rule(
        self,
        machine_id: UUID,
        rule: AlertRule,
        value: float | None,
        threshold: float,
        *,
        commit: bool = True,
    ) -> int:
        existing_alert = self.repository.get_active_alert(
            machine_id=machine_id,
            alert_type=rule.alert_type,
        )
        is_abnormal = value is not None and rule.is_abnormal(
            value,
            threshold,
        )

        if is_abnormal:
            if existing_alert is None:
                self.repository.create_alert(
                    machine_id=machine_id,
                    severity=rule.severity,
                    alert_type=rule.alert_type,
                    message=rule.message,
                    commit=commit,
                )

                return 1
        elif existing_alert is not None:
            self.repository.resolve_alert(
                existing_alert,
                commit=commit,
            )

        return 0
