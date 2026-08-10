from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MachineFleetItemResponse(BaseModel):
    id: UUID
    name: str
    serial_number: str
    production_line: str
    health_status: str
    health_score: int


class MachineDetailResponse(BaseModel):
    id: UUID
    name: str
    serial_number: str
    production_line: str
    health_status: str
    health_score: int
    temperature: float | None
    pressure: float | None
    vibration: float | None
    rpm: float | None
    energy: float | None
    warnings: list[str]


class TelemetryTrendPoint(BaseModel):
    recorded_at: datetime
    value: float


class MachineTrendsResponse(BaseModel):
    machine_id: UUID
    machine_name: str
    temperature: list[TelemetryTrendPoint]
    pressure: list[TelemetryTrendPoint]
    vibration: list[TelemetryTrendPoint]
    rpm: list[TelemetryTrendPoint]
    energy: list[TelemetryTrendPoint]
