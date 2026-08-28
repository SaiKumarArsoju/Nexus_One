from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertSeverity, AlertStatus, Machine


class AlertRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active_alerts(self):
        statement = (
            select(
                Alert.id,
                Alert.machine_id,
                Machine.name.label("machine_name"),
                Alert.severity,
                Alert.status,
                Alert.alert_type,
                Alert.message,
                Alert.created_at,
            )
            .join(Machine, Alert.machine_id == Machine.id)
            .where(
                Alert.status.in_(
                    [
                        AlertStatus.ACTIVE,
                        AlertStatus.ACKNOWLEDGED,
                    ]
                )
            )
            .order_by(Alert.created_at.desc())
        )

        return self.db.execute(statement).all()

    def get_active_alert(
        self,
        machine_id: UUID,
        alert_type: str,
    ) -> Alert | None:
        statement = select(Alert).where(
            Alert.machine_id == machine_id,
            Alert.alert_type == alert_type,
            Alert.status.in_(
                [
                    AlertStatus.ACTIVE,
                    AlertStatus.ACKNOWLEDGED,
                ]
            ),
        )

        return self.db.scalar(statement)

    def get_alert_history(self):
        statement = (
            select(
                Alert.id,
                Alert.machine_id,
                Machine.name.label("machine_name"),
                Alert.severity,
                Alert.status,
                Alert.alert_type,
                Alert.message,
                Alert.created_at,
            )
            .join(Machine, Alert.machine_id == Machine.id)
            .order_by(Alert.created_at.desc())
        )

        return self.db.execute(statement).all()

    def get_alert_by_id(
        self,
        alert_id: UUID,
    ) -> Alert | None:
        statement = select(Alert).where(Alert.id == alert_id)

        return self.db.scalar(statement)

    def create_alert(
        self,
        machine_id: UUID,
        severity: AlertSeverity,
        alert_type: str,
        message: str,
        *,
        commit: bool = True,
    ) -> Alert:
        alert = Alert(
            machine_id=machine_id,
            severity=severity,
            status=AlertStatus.ACTIVE,
            alert_type=alert_type,
            message=message,
        )

        self.db.add(alert)

        if commit:
            self.db.commit()
            self.db.refresh(alert)
        else:
            self.db.flush()

        return alert

    def acknowledge_alert(
        self,
        alert: Alert,
    ) -> Alert:
        alert.status = AlertStatus.ACKNOWLEDGED

        self.db.commit()
        self.db.refresh(alert)

        return alert

    def resolve_alert(
        self,
        alert: Alert,
        *,
        commit: bool = True,
    ) -> Alert:
        alert.status = AlertStatus.RESOLVED

        if commit:
            self.db.commit()
            self.db.refresh(alert)
        else:
            self.db.flush()

        return alert
