from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.machine_health import calculate_machine_health
from app.repositories import MachineRepository
from app.schemas import MachineDetailResponse, MachineFleetItemResponse


class MachineService:
    def __init__(self, db: Session) -> None:
        self.repository = MachineRepository(db)

    def get_fleet(self) -> list[MachineFleetItemResponse]:
        machines = self.repository.get_all_machines_with_lines()
        latest_readings = self.repository.get_latest_sensor_readings()

        machine_values: dict = defaultdict(dict)

        for reading in latest_readings:
            machine_values[reading.machine_id][reading.sensor_type] = reading.value

        fleet = []

        for machine in machines:
            values: dict[SensorType, float] = machine_values.get(machine.id, {})
            health = calculate_machine_health(values)

            fleet.append(
                MachineFleetItemResponse(
                    id=machine.id,
                    name=machine.name,
                    serial_number=machine.serial_number,
                    production_line=machine.production_line,
                    health_status=health.status,
                    health_score=health.score,
                )
            )

        return fleet

    def get_machine_detail(self, machine_id):
        machines = self.repository.get_all_machines_with_lines()
        latest_readings = self.repository.get_latest_sensor_readings()

        machine = next(
            (item for item in machines if item.id == machine_id),
            None,
        )

        if machine is None:
            return None

        values = {}

        for reading in latest_readings:
            if reading.machine_id == machine_id:
                values[reading.sensor_type] = reading.value

        health = calculate_machine_health(values)

        temperature = values.get(SensorType.TEMPERATURE)
        pressure = values.get(SensorType.PRESSURE)
        vibration = values.get(SensorType.VIBRATION)
        rpm = values.get(SensorType.RPM)
        energy = values.get(SensorType.ENERGY)

        warnings = []

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

        return MachineDetailResponse(
            id=machine.id,
            name=machine.name,
            serial_number=machine.serial_number,
            production_line=machine.production_line,
            health_status=health.status,
            health_score=health.score,
            temperature=temperature,
            pressure=pressure,
            vibration=vibration,
            rpm=rpm,
            energy=energy,
            warnings=warnings,
        )
