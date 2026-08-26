from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import SensorType
from app.models import AlertSeverity


class AlertThresholdUpdate(BaseModel):
    threshold_value: float = Field(
        gt=0,
        allow_inf_nan=False,
    )


class AlertThresholdResponse(BaseModel):
    sensor_type: SensorType
    threshold_value: float
    unit: str
    severity: AlertSeverity
    alert_type: str
    updated_at: datetime
