from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: UUID
    machine_id: UUID
    machine_name: str
    severity: str
    status: str
    alert_type: str
    message: str
    created_at: datetime
