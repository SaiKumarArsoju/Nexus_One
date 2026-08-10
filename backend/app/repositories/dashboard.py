from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Factory, Machine, ProductionLine, Sensor, SensorReading


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_factories_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Factory)) or 0

    def get_production_lines_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(ProductionLine)) or 0

    def get_machines_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Machine)) or 0

    def get_sensors_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Sensor)) or 0

    def get_sensor_readings_count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(SensorReading)) or 0

    def get_all_machines(self) -> list[Machine]:
        return list(self.db.scalars(select(Machine)).all())

    def get_latest_sensor_readings(self):
        latest_timestamp_subquery = (
            select(
                SensorReading.sensor_id,
                func.max(SensorReading.recorded_at).label("latest_recorded_at"),
            )
            .group_by(SensorReading.sensor_id)
            .subquery()
        )

        statement = (
            select(
                Sensor.machine_id,
                Sensor.sensor_type,
                SensorReading.value,
            )
            .join(SensorReading, SensorReading.sensor_id == Sensor.id)
            .join(
                latest_timestamp_subquery,
                (latest_timestamp_subquery.c.sensor_id == SensorReading.sensor_id)
                & (latest_timestamp_subquery.c.latest_recorded_at == SensorReading.recorded_at),
            )
        )

        return self.db.execute(statement).all()
