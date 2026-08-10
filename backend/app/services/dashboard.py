from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.repositories import DashboardRepository
from app.schemas import DashboardSummaryResponse


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.repository = DashboardRepository(db)

    def get_summary(self) -> DashboardSummaryResponse:
        healthy_machines = 0
        warning_machines = 0
        critical_machines = 0

        latest_readings = self.repository.get_latest_sensor_readings()

        machine_values: dict = defaultdict(dict)

        for row in latest_readings:
            machine_values[row.machine_id][row.sensor_type] = row.value

        for values in machine_values.values():
            health_score = 100

            temperature = values.get(SensorType.TEMPERATURE)
            pressure = values.get(SensorType.PRESSURE)
            vibration = values.get(SensorType.VIBRATION)
            rpm = values.get(SensorType.RPM)
            energy = values.get(SensorType.ENERGY)

            if temperature is not None and temperature > 90:
                health_score -= 20

            if pressure is not None and pressure > 7.5:
                health_score -= 15

            if vibration is not None and vibration > 0.4:
                health_score -= 25

            if rpm is not None and rpm > 2800:
                health_score -= 15

            if energy is not None and energy > 28:
                health_score -= 10

            health_score = max(health_score, 0)

            if health_score >= 85:
                healthy_machines += 1
            elif health_score >= 60:
                warning_machines += 1
            else:
                critical_machines += 1

        return DashboardSummaryResponse(
            factories=self.repository.get_factories_count(),
            production_lines=self.repository.get_production_lines_count(),
            machines=self.repository.get_machines_count(),
            sensors=self.repository.get_sensors_count(),
            sensor_readings=self.repository.get_sensor_readings_count(),
            healthy_machines=healthy_machines,
            warning_machines=warning_machines,
            critical_machines=critical_machines,
        )
