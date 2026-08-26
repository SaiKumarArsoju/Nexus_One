from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.alert_rules import (
    get_abnormal_alert_rules,
    validate_threshold_map,
)
from app.domain.machine_health import calculate_machine_health
from app.repositories import AlertThresholdRepository, MachineHealthRepository
from app.schemas import MachineHealthResponse


class MachineHealthService:
    def __init__(self, db: Session) -> None:
        self.repository = MachineHealthRepository(db)
        self.threshold_repository = AlertThresholdRepository(db)

    def get_health(self, machine_id: UUID) -> MachineHealthResponse:
        machine = self.repository.get_machine(machine_id)

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Machine not found",
            )

        latest_readings = self.repository.get_latest_sensor_readings(machine_id)
        latest_values: dict[SensorType, float] = {
            reading.sensor_type: reading.value for reading in latest_readings
        }

        thresholds = self.threshold_repository.get_threshold_map()
        validate_threshold_map(thresholds)
        health = calculate_machine_health(latest_values, thresholds)

        temperature = latest_values.get(SensorType.TEMPERATURE)
        pressure = latest_values.get(SensorType.PRESSURE)
        vibration = latest_values.get(SensorType.VIBRATION)
        rpm = latest_values.get(SensorType.RPM)
        energy = latest_values.get(SensorType.ENERGY)

        warnings = [rule.message for rule in get_abnormal_alert_rules(latest_values, thresholds)]

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
