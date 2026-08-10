from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Machine, ProductionLine, Sensor, SensorReading


class MachineRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_machines_with_lines(self):
        statement = (
            select(
                Machine.id,
                Machine.name,
                Machine.serial_number,
                ProductionLine.name.label("production_line"),
            )
            .join(
                ProductionLine,
                Machine.production_line_id == ProductionLine.id,
            )
            .order_by(Machine.name)
        )

        return self.db.execute(statement).all()

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
