from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Machine, Sensor, SensorReading


@dataclass(frozen=True)
class TelemetryAggregateBucket:
    bucket_start: datetime
    average: float
    minimum: float
    maximum: float
    count: int


class TelemetryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_machine(self, machine_id: UUID) -> Machine | None:
        return self.db.get(Machine, machine_id)

    def get_sensor(self, sensor_id: UUID) -> Sensor | None:
        return self.db.get(Sensor, sensor_id)

    def create_reading(
        self,
        sensor_id: UUID,
        value: float,
        recorded_at: datetime,
    ) -> SensorReading:
        reading = SensorReading(
            sensor_id=sensor_id,
            value=value,
            recorded_at=recorded_at,
        )

        self.db.add(reading)
        self.db.flush()

        return reading

    def list_readings(
        self,
        *,
        sensor_id: UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int,
    ) -> list[SensorReading]:
        statement = select(SensorReading).where(SensorReading.sensor_id == sensor_id)

        if start is not None:
            statement = statement.where(SensorReading.recorded_at >= start)

        if end is not None:
            statement = statement.where(SensorReading.recorded_at <= end)

        newest_readings = self.db.scalars(
            statement.order_by(
                SensorReading.recorded_at.desc(),
                SensorReading.id.desc(),
            ).limit(limit)
        ).all()

        return list(reversed(newest_readings))

    def aggregate_readings(
        self,
        *,
        sensor_id: UUID,
        start: datetime,
        end: datetime,
        bucket_duration: timedelta,
    ) -> list[TelemetryAggregateBucket]:
        bucket_start = func.date_bin(
            bucket_duration,
            SensorReading.recorded_at,
            datetime(1970, 1, 1, tzinfo=UTC),
        ).label("bucket_start")

        statement = (
            select(
                bucket_start,
                func.avg(SensorReading.value).label("average"),
                func.min(SensorReading.value).label("minimum"),
                func.max(SensorReading.value).label("maximum"),
                func.count().label("count"),
            )
            .where(
                SensorReading.sensor_id == sensor_id,
                SensorReading.recorded_at >= start,
                SensorReading.recorded_at < end,
            )
            .group_by(bucket_start)
            .order_by(bucket_start.asc())
        )

        return [
            TelemetryAggregateBucket(
                bucket_start=row.bucket_start,
                average=float(row.average),
                minimum=float(row.minimum),
                maximum=float(row.maximum),
                count=row.count,
            )
            for row in self.db.execute(statement)
        ]

    def get_machine_telemetry(self, machine_id: UUID):
        statement = (
            select(
                SensorReading.sensor_id,
                Sensor.name,
                Sensor.sensor_type,
                Sensor.unit,
                SensorReading.value,
                SensorReading.recorded_at,
            )
            .join(Sensor)
            .where(Sensor.machine_id == machine_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(100)
        )

        return self.db.execute(statement).all()
