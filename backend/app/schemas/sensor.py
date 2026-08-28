from uuid import UUID

from pydantic import BaseModel

from app.core.enums import SensorType


class SensorDiscoveryResponse(BaseModel):
    id: UUID
    name: str
    sensor_type: SensorType
    unit: str
    machine_id: UUID
