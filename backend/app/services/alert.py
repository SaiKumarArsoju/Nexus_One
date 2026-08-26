from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.models import AlertSeverity, AlertStatus
from app.repositories import AlertRepository, MachineRepository
from app.schemas import AlertResponse


class AlertService:
    def __init__(self, db: Session) -> None:
        self.repository = AlertRepository(db)
        self.machine_repository = MachineRepository(db)

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
        latest_readings = self.machine_repository.get_latest_sensor_readings()

        machine_values: dict = {}

        for reading in latest_readings:
            machine_values.setdefault(reading.machine_id, {})
            machine_values[reading.machine_id][reading.sensor_type] = reading.value

        created_count = 0

        for machine_id, values in machine_values.items():
            conditions = [
                (
                    "HIGH_TEMPERATURE",
                    values.get(SensorType.TEMPERATURE),
                    90,
                    AlertSeverity.WARNING,
                    "High temperature detected",
                ),
                (
                    "HIGH_PRESSURE",
                    values.get(SensorType.PRESSURE),
                    7.5,
                    AlertSeverity.WARNING,
                    "High pressure detected",
                ),
                (
                    "HIGH_VIBRATION",
                    values.get(SensorType.VIBRATION),
                    0.4,
                    AlertSeverity.CRITICAL,
                    "High vibration detected",
                ),
                (
                    "HIGH_RPM",
                    values.get(SensorType.RPM),
                    2800,
                    AlertSeverity.WARNING,
                    "High RPM detected",
                ),
                (
                    "HIGH_ENERGY",
                    values.get(SensorType.ENERGY),
                    28,
                    AlertSeverity.WARNING,
                    "High energy consumption detected",
                ),
            ]

            for alert_type, value, threshold, severity, message in conditions:
                existing_alert = self.repository.get_active_alert(
                    machine_id=machine_id,
                    alert_type=alert_type,
                )

                is_abnormal = value is not None and value > threshold

                if is_abnormal:
                    if existing_alert is None:
                        self.repository.create_alert(
                            machine_id=machine_id,
                            severity=severity,
                            alert_type=alert_type,
                            message=message,
                        )

                        created_count += 1

                elif existing_alert is not None:
                    self.repository.resolve_alert(existing_alert)

        return created_count
