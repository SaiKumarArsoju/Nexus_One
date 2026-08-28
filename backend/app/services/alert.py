from dataclasses import dataclass
from typing import Literal
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
from app.models import Alert, AlertStatus
from app.realtime import CommittedOperation, PendingRealtimeEvent, alert_event
from app.repositories import (
    AlertRepository,
    AlertThresholdRepository,
    MachineRepository,
)
from app.schemas import AlertResponse


@dataclass(frozen=True)
class AlertStateChange:
    event_type: Literal["alert.created", "alert.updated"]
    alert_id: UUID
    machine_id: UUID
    status: AlertStatus

    def to_realtime_event(self) -> PendingRealtimeEvent:
        return alert_event(
            event_type=self.event_type,
            alert_id=str(self.alert_id),
            machine_id=str(self.machine_id),
            status=self.status.value,
        )


class AlertService:
    def __init__(self, db: Session) -> None:
        self.db = db
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
        return self.acknowledge_alert_operation(alert_id).result

    def acknowledge_alert_operation(
        self,
        alert_id: UUID,
    ) -> CommittedOperation[AlertResponse]:
        alert = self.repository.get_alert_by_id(alert_id)

        if alert is None:
            raise LookupError("Alert not found")

        if alert.status == AlertStatus.RESOLVED:
            raise ValueError("Resolved alerts cannot be acknowledged")

        events: tuple[PendingRealtimeEvent, ...] = ()

        if alert.status == AlertStatus.ACTIVE:
            alert = self.repository.acknowledge_alert(alert)
            events = (
                AlertStateChange(
                    event_type="alert.updated",
                    alert_id=alert.id,
                    machine_id=alert.machine_id,
                    status=alert.status,
                ).to_realtime_event(),
            )

        return CommittedOperation(
            result=self._to_response(alert),
            events=events,
        )

    def resolve_alert(
        self,
        alert_id: UUID,
    ) -> AlertResponse:
        return self.resolve_alert_operation(alert_id).result

    def resolve_alert_operation(
        self,
        alert_id: UUID,
    ) -> CommittedOperation[AlertResponse]:
        alert = self.repository.get_alert_by_id(alert_id)

        if alert is None:
            raise LookupError("Alert not found")

        events: tuple[PendingRealtimeEvent, ...] = ()

        if alert.status != AlertStatus.RESOLVED:
            alert = self.repository.resolve_alert(alert)
            events = (
                AlertStateChange(
                    event_type="alert.updated",
                    alert_id=alert.id,
                    machine_id=alert.machine_id,
                    status=alert.status,
                ).to_realtime_event(),
            )

        return CommittedOperation(
            result=self._to_response(alert),
            events=events,
        )

    def sync_machine_alerts(self) -> int:
        return self.sync_machine_alerts_operation().result

    def sync_machine_alerts_operation(self) -> CommittedOperation[int]:
        thresholds = self.threshold_repository.get_threshold_map()
        validate_threshold_map(thresholds)
        latest_readings = self.machine_repository.get_latest_sensor_readings()

        machine_values: dict = {}

        for reading in latest_readings:
            machine_values.setdefault(reading.machine_id, {})
            machine_values[reading.machine_id][reading.sensor_type] = reading.value

        changes: list[AlertStateChange] = []

        for machine_id, values in machine_values.items():
            for rule in ALERT_RULES:
                change = self._apply_alert_rule(
                    machine_id=machine_id,
                    rule=rule,
                    value=values.get(rule.sensor_type),
                    threshold=thresholds[rule.sensor_type],
                    commit=False,
                )

                if change is not None:
                    changes.append(change)

        if changes:
            self.db.commit()

        return CommittedOperation(
            result=sum(change.event_type == "alert.created" for change in changes),
            events=tuple(change.to_realtime_event() for change in changes),
        )

    def evaluate_sensor_reading(
        self,
        machine_id: UUID,
        sensor_type: SensorType,
        value: float,
        *,
        commit: bool = True,
    ) -> bool:
        change = self.evaluate_sensor_reading_change(
            machine_id=machine_id,
            sensor_type=sensor_type,
            value=value,
            commit=commit,
        )

        return change is not None and change.event_type == "alert.created"

    def evaluate_sensor_reading_change(
        self,
        machine_id: UUID,
        sensor_type: SensorType,
        value: float,
        *,
        commit: bool = True,
    ) -> AlertStateChange | None:
        threshold = self.threshold_repository.get_by_sensor_type(sensor_type)

        if threshold is None:
            raise AlertThresholdConfigurationError(
                f"Missing persisted alert threshold for: {sensor_type.value}"
            )

        return self._apply_alert_rule(
            machine_id=machine_id,
            rule=ALERT_RULES_BY_SENSOR_TYPE[sensor_type],
            value=value,
            threshold=threshold.threshold_value,
            commit=commit,
        )

    def _apply_alert_rule(
        self,
        machine_id: UUID,
        rule: AlertRule,
        value: float | None,
        threshold: float,
        *,
        commit: bool = True,
    ) -> AlertStateChange | None:
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
                alert = self.repository.create_alert(
                    machine_id=machine_id,
                    severity=rule.severity,
                    alert_type=rule.alert_type,
                    message=rule.message,
                    commit=commit,
                )

                return AlertStateChange(
                    event_type="alert.created",
                    alert_id=alert.id,
                    machine_id=alert.machine_id,
                    status=alert.status,
                )
        elif existing_alert is not None:
            alert = self.repository.resolve_alert(
                existing_alert,
                commit=commit,
            )

            return AlertStateChange(
                event_type="alert.updated",
                alert_id=alert.id,
                machine_id=alert.machine_id,
                status=alert.status,
            )

        return None

    @staticmethod
    def _to_response(alert: Alert) -> AlertResponse:
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
