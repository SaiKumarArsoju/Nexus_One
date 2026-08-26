from collections import defaultdict

from sqlalchemy.orm import Session

from app.domain.alert_rules import validate_threshold_map
from app.domain.machine_health import calculate_machine_health
from app.repositories import AlertThresholdRepository, DashboardRepository
from app.schemas import DashboardSummaryResponse


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.repository = DashboardRepository(db)
        self.threshold_repository = AlertThresholdRepository(db)

    def get_summary(self) -> DashboardSummaryResponse:
        healthy_machines = 0
        warning_machines = 0
        critical_machines = 0

        thresholds = self.threshold_repository.get_threshold_map()
        validate_threshold_map(thresholds)
        latest_readings = self.repository.get_latest_sensor_readings()

        machine_values: dict = defaultdict(dict)

        for reading in latest_readings:
            machine_values[reading.machine_id][reading.sensor_type] = reading.value

        for values in machine_values.values():
            health = calculate_machine_health(values, thresholds)

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
            active_alerts=self.repository.get_active_alerts_count(),
            warning_alerts=self.repository.get_warning_alerts_count(),
            critical_alerts=self.repository.get_critical_alerts_count(),
            resolved_alerts=self.repository.get_resolved_alerts_count(),
        )
