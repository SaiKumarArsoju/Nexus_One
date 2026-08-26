from datetime import datetime

from pydantic import BaseModel

from app.core.enums import SensorType
from app.models import AlertSeverity


class AlertThresholdResponse(BaseModel):
    sensor_type: SensorType
    threshold_value: float
    unit: str
    severity: AlertSeverity
    alert_type: str
    updated_at: datetime
