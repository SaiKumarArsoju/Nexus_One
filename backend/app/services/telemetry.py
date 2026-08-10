from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Machine, Sensor, SensorReading
from app.schemas import TelemetryReadingResponse


class TelemetryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_machine_telemetry(
        self,
        machine_id: UUID,
    ) -> list[TelemetryReadingResponse]:

        machine = self.db.get(Machine, machine_id)

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Machine not found",
            )

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

        rows = self.db.execute(statement).all()

        return [
            TelemetryReadingResponse(
                sensor_id=row.sensor_id,
                sensor_name=row.name,
                sensor_type=row.sensor_type.value,
                unit=row.unit,
                value=row.value,
                recorded_at=row.recorded_at,
            )
            for row in rows
        ]
