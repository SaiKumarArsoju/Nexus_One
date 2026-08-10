from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TelemetryReadingResponse(BaseModel):
    sensor_id: UUID
    sensor_name: str
    sensor_type: str
    unit: str
    value: float
    recorded_at: datetime
