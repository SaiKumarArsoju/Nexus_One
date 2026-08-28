from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Sensor


class SensorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_sensors(self) -> list[Sensor]:
        statement = select(Sensor).order_by(
            Sensor.machine_id,
            Sensor.sensor_type,
            Sensor.name,
            Sensor.id,
        )

        return list(self.db.scalars(statement).all())
