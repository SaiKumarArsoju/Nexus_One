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
