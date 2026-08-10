from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    factories: int
    production_lines: int
    machines: int
    sensors: int
    sensor_readings: int
    healthy_machines: int
    warning_machines: int
    critical_machines: int
    active_alerts: int
    warning_alerts: int
    critical_alerts: int
    resolved_alerts: int
