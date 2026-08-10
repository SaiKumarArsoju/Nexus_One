from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Machine, Sensor, SensorReading


class TelemetryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_machine(self, machine_id: UUID) -> Machine | None:
        return self.db.get(Machine, machine_id)

    def get_machine_telemetry(self, machine_id: UUID):
        statement = (
            select(
                SensorReading.sensor_id,
                Sensor.name,
                Sensor.sensor_type,
                Sensor.unit,
                SensorReading.value,
                SensorReading.recorded_at,
            )
            .join(Sensor)
            .where(Sensor.machine_id == machine_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(100)
        )

        return self.db.execute(statement).all()
