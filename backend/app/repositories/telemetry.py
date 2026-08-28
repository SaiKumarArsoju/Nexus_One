from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Machine, Sensor, SensorReading


class TelemetryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_machine(self, machine_id: UUID) -> Machine | None:
        return self.db.get(Machine, machine_id)

    def get_sensor(self, sensor_id: UUID) -> Sensor | None:
        return self.db.get(Sensor, sensor_id)

    def create_reading(
        self,
        sensor_id: UUID,
        value: float,
        recorded_at: datetime,
    ) -> SensorReading:
        reading = SensorReading(
            sensor_id=sensor_id,
            value=value,
            recorded_at=recorded_at,
        )

        self.db.add(reading)
        self.db.flush()

        return reading

    def list_readings(
        self,
        *,
        sensor_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int,
    ) -> list[SensorReading]:
        statement = select(SensorReading).where(SensorReading.sensor_id == sensor_id)

        if start is not None:
            statement = statement.where(SensorReading.recorded_at >= start)

        if end is not None:
            statement = statement.where(SensorReading.recorded_at <= end)

        newest_readings = self.db.scalars(
            statement.order_by(
                SensorReading.recorded_at.desc(),
                SensorReading.id.desc(),
            ).limit(limit)
        ).all()

        return list(reversed(newest_readings))

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
