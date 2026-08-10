from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import Machine, Sensor, SensorReading
from app.schemas import TelemetryReadingResponse

router = APIRouter(prefix="/api/v1", tags=["Telemetry"])


@router.get(
    "/machines/{machine_id}/telemetry",
    response_model=list[TelemetryReadingResponse],
)
def get_machine_telemetry(machine_id: UUID):
    with SessionLocal() as db:
        machine = db.get(Machine, machine_id)

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

        rows = db.execute(statement).all()

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
