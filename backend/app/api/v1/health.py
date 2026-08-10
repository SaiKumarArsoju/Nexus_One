from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.enums import SensorType
from app.database.session import SessionLocal
from app.models import Machine, Sensor, SensorReading
from app.schemas import MachineHealthResponse

router = APIRouter(prefix="/api/v1", tags=["Machine Health"])


@router.get(
    "/machines/{machine_id}/health",
    response_model=MachineHealthResponse,
)
def get_machine_health(machine_id: UUID) -> MachineHealthResponse:
    with SessionLocal() as db:
        machine = db.get(Machine, machine_id)

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Machine not found",
            )

        sensors = db.scalars(select(Sensor).where(Sensor.machine_id == machine_id)).all()

        latest_values: dict[SensorType, float] = {}

        for sensor in sensors:
            reading = db.scalar(
                select(SensorReading)
                .where(SensorReading.sensor_id == sensor.id)
                .order_by(SensorReading.recorded_at.desc())
                .limit(1)
            )

            if reading is not None:
                latest_values[sensor.sensor_type] = reading.value

        warnings: list[str] = []
        health_score = 100

        temperature = latest_values.get(SensorType.TEMPERATURE)
        pressure = latest_values.get(SensorType.PRESSURE)
        vibration = latest_values.get(SensorType.VIBRATION)
        rpm = latest_values.get(SensorType.RPM)
        energy = latest_values.get(SensorType.ENERGY)

        if temperature is not None and temperature > 90:
            warnings.append("High temperature detected")
            health_score -= 20

        if pressure is not None and pressure > 7.5:
            warnings.append("High pressure detected")
            health_score -= 15

        if vibration is not None and vibration > 0.4:
            warnings.append("High vibration detected")
            health_score -= 25

        if rpm is not None and rpm > 2800:
            warnings.append("High RPM detected")
            health_score -= 15

        if energy is not None and energy > 28:
            warnings.append("High energy consumption detected")
            health_score -= 10

        health_score = max(health_score, 0)

        if health_score >= 85:
            status = "HEALTHY"
        elif health_score >= 60:
            status = "WARNING"
        else:
            status = "CRITICAL"

        if warnings:
            recommendation = "Review the detected conditions and inspect the machine."
        else:
            recommendation = "Machine operating within acceptable limits."

        return MachineHealthResponse(
            machine_name=machine.name,
            status=status,
            overall_health=health_score,
            temperature=temperature,
            pressure=pressure,
            vibration=vibration,
            rpm=rpm,
            energy=energy,
            warnings=warnings,
            recommendation=recommendation,
        )
