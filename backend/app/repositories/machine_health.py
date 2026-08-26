from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Machine, Sensor, SensorReading


class MachineHealthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_machine(self, machine_id: UUID) -> Machine | None:
        return self.db.get(Machine, machine_id)

    def get_machine_sensors(self, machine_id: UUID):
        return self.db.scalars(select(Sensor).where(Sensor.machine_id == machine_id)).all()

    def get_latest_reading(self, sensor_id: UUID) -> SensorReading | None:
        return self.db.scalar(
            select(SensorReading)
            .where(SensorReading.sensor_id == sensor_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(1)
        )

    def get_latest_sensor_readings(self, machine_id: UUID):
        latest_timestamp_subquery = (
            select(
                SensorReading.sensor_id,
                func.max(SensorReading.recorded_at).label("latest_recorded_at"),
            )
            .group_by(SensorReading.sensor_id)
            .subquery()
        )

        statement = (
            select(
                Sensor.sensor_type,
                SensorReading.value,
            )
            .join(SensorReading, SensorReading.sensor_id == Sensor.id)
            .join(
                latest_timestamp_subquery,
                (latest_timestamp_subquery.c.sensor_id == SensorReading.sensor_id)
                & (latest_timestamp_subquery.c.latest_recorded_at == SensorReading.recorded_at),
            )
            .where(Sensor.machine_id == machine_id)
        )

        return self.db.execute(statement).all()
