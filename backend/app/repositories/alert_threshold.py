from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.models import AlertThreshold


class AlertThresholdRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[AlertThreshold]:
        statement = select(AlertThreshold).order_by(AlertThreshold.sensor_type)

        return list(self.db.scalars(statement))

    def get_threshold_map(self) -> dict[SensorType, float]:
        return {threshold.sensor_type: threshold.threshold_value for threshold in self.get_all()}

    def get_by_sensor_type(
        self,
        sensor_type: SensorType,
    ) -> AlertThreshold | None:
        return self.db.get(AlertThreshold, sensor_type)
