from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field


class TelemetryReadingCreate(BaseModel):
    sensor_id: UUID
    value: float = Field(allow_inf_nan=False)
    recorded_at: AwareDatetime


class TelemetryIngestedReadingResponse(BaseModel):
    id: UUID
    sensor_id: UUID
    value: float
    recorded_at: datetime


class TelemetryReadingResponse(BaseModel):
    sensor_id: UUID
    sensor_name: str
    sensor_type: str
    unit: str
    value: float
    recorded_at: datetime
