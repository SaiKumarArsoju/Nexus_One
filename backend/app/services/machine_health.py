from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.machine_health import calculate_machine_health
from app.repositories import MachineHealthRepository
from app.schemas import MachineHealthResponse


class MachineHealthService:
    def __init__(self, db: Session) -> None:
        self.repository = MachineHealthRepository(db)

    def get_health(self, machine_id: UUID) -> MachineHealthResponse:
        machine = self.repository.get_machine(machine_id)

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Machine not found",
            )

        sensors = self.repository.get_machine_sensors(machine_id)

        latest_values: dict[SensorType, float] = {}

        for sensor in sensors:
            reading = self.repository.get_latest_reading(sensor.id)

            if reading is not None:
                latest_values[sensor.sensor_type] = reading.value

        health = calculate_machine_health(latest_values)

        warnings: list[str] = []

        temperature = latest_values.get(SensorType.TEMPERATURE)
        pressure = latest_values.get(SensorType.PRESSURE)
        vibration = latest_values.get(SensorType.VIBRATION)
        rpm = latest_values.get(SensorType.RPM)
        energy = latest_values.get(SensorType.ENERGY)

        if temperature is not None and temperature > 90:
            warnings.append("High temperature detected")

        if pressure is not None and pressure > 7.5:
            warnings.append("High pressure detected")

        if vibration is not None and vibration > 0.4:
            warnings.append("High vibration detected")

        if rpm is not None and rpm > 2800:
            warnings.append("High RPM detected")

        if energy is not None and energy > 28:
            warnings.append("High energy consumption detected")

        recommendation = (
            "Review the detected conditions and inspect the machine."
            if warnings
            else "Machine operating within acceptable limits."
        )

        return MachineHealthResponse(
            machine_name=machine.name,
            status=health.status,
            overall_health=health.score,
            temperature=temperature,
            pressure=pressure,
            vibration=vibration,
            rpm=rpm,
            energy=energy,
            warnings=warnings,
            recommendation=recommendation,
        )
