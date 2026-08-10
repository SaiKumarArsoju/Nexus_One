from sqlalchemy.orm import Session

from app.repositories import DashboardRepository
from app.schemas import DashboardSummaryResponse
from app.services.machine_health import MachineHealthService


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.repository = DashboardRepository(db)
        self.machine_health_service = MachineHealthService(db)

    def get_summary(self) -> DashboardSummaryResponse:
        healthy_machines = 0
        warning_machines = 0
        critical_machines = 0

        machines = self.repository.get_all_machines()

        for machine in machines:
            health = self.machine_health_service.get_health(machine.id)

            if health.status == "HEALTHY":
                healthy_machines += 1
            elif health.status == "WARNING":
                warning_machines += 1
            elif health.status == "CRITICAL":
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
