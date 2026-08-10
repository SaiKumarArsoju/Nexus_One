from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.machine_health import calculate_machine_health
from app.repositories import MachineRepository
from app.schemas import MachineFleetItemResponse


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
