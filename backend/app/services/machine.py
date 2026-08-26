from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.domain.alert_rules import (
    get_abnormal_alert_rules,
    validate_threshold_map,
)
from app.domain.machine_health import calculate_machine_health
from app.repositories import AlertThresholdRepository, MachineRepository
from app.schemas import (
    MachineDetailResponse,
    MachineFleetItemResponse,
    MachineTrendsResponse,
    TelemetryTrendPoint,
)


class MachineService:
    def __init__(self, db: Session) -> None:
        self.repository = MachineRepository(db)
        self.threshold_repository = AlertThresholdRepository(db)

    def get_fleet(self) -> list[MachineFleetItemResponse]:
        machines = self.repository.get_all_machines_with_lines()
        latest_readings = self.repository.get_latest_sensor_readings()
        thresholds = self.threshold_repository.get_threshold_map()
        validate_threshold_map(thresholds)

        machine_values: dict = defaultdict(dict)

        for reading in latest_readings:
            machine_values[reading.machine_id][reading.sensor_type] = reading.value

        fleet = []

        for machine in machines:
            values: dict[SensorType, float] = machine_values.get(machine.id, {})
            health = calculate_machine_health(values, thresholds)

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

        thresholds = self.threshold_repository.get_threshold_map()
        validate_threshold_map(thresholds)
        health = calculate_machine_health(values, thresholds)

        temperature = values.get(SensorType.TEMPERATURE)
        pressure = values.get(SensorType.PRESSURE)
        vibration = values.get(SensorType.VIBRATION)
        rpm = values.get(SensorType.RPM)
        energy = values.get(SensorType.ENERGY)

        warnings = [rule.message for rule in get_abnormal_alert_rules(values, thresholds)]

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

    def get_machine_trends(
        self,
        machine_id,
    ) -> MachineTrendsResponse | None:
        machines = self.repository.get_all_machines_with_lines()

        machine = next(
            (item for item in machines if item.id == machine_id),
            None,
        )

        if machine is None:
            return None

        grouped = self.repository.get_machine_trends(machine_id)

        def convert(sensor_type: SensorType) -> list[TelemetryTrendPoint]:
            rows = grouped.get(sensor_type, [])

            return [
                TelemetryTrendPoint(
                    recorded_at=row.recorded_at,
                    value=row.value,
                )
                for row in reversed(rows)
            ]

        return MachineTrendsResponse(
            machine_id=machine.id,
            machine_name=machine.name,
            temperature=convert(SensorType.TEMPERATURE),
            pressure=convert(SensorType.PRESSURE),
            vibration=convert(SensorType.VIBRATION),
            rpm=convert(SensorType.RPM),
            energy=convert(SensorType.ENERGY),
        )
