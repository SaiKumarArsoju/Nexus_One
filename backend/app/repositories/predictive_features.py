from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.models import Machine, Sensor, SensorReading


@dataclass(frozen=True)
class SensorFeatureAggregate:
    sensor_id: UUID
    reading_count: int
    mean: float
    minimum: float
    maximum: float
    standard_deviation: float
    first_value: float
    last_value: float
    first_recorded_at: datetime
    last_recorded_at: datetime
    exceeding_reading_count: int


class PredictiveFeatureRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_machine(self, machine_id: UUID) -> Machine | None:
        return self.db.get(Machine, machine_id)

    def list_machine_sensors(self, machine_id: UUID) -> list[Sensor]:
        statement = (
            select(Sensor)
            .where(Sensor.machine_id == machine_id)
            .order_by(Sensor.sensor_type, Sensor.name, Sensor.id)
        )
        return list(self.db.scalars(statement))

    def aggregate_machine_sensor_features(
        self,
        *,
        machine_id: UUID,
        start: datetime,
        end: datetime,
        thresholds: Mapping[SensorType, float],
    ) -> list[SensorFeatureAggregate]:
        threshold_value = case(
            *[
                (Sensor.sensor_type == sensor_type, value)
                for sensor_type, value in thresholds.items()
            ]
        )
        ordered_values = func.array_agg(
            aggregate_order_by(
                SensorReading.value,
                SensorReading.recorded_at.asc(),
                SensorReading.id.asc(),
            )
        )
        reverse_ordered_values = func.array_agg(
            aggregate_order_by(
                SensorReading.value,
                SensorReading.recorded_at.desc(),
                SensorReading.id.desc(),
            )
        )
        statement = (
            select(
                Sensor.id.label("sensor_id"),
                func.count().label("reading_count"),
                func.avg(SensorReading.value).label("mean"),
                func.min(SensorReading.value).label("minimum"),
                func.max(SensorReading.value).label("maximum"),
                func.stddev_pop(SensorReading.value).label("standard_deviation"),
                ordered_values[1].label("first_value"),
                reverse_ordered_values[1].label("last_value"),
                func.min(SensorReading.recorded_at).label("first_recorded_at"),
                func.max(SensorReading.recorded_at).label("last_recorded_at"),
                func.count()
                .filter(SensorReading.value > threshold_value)
                .label("exceeding_reading_count"),
            )
            .join(SensorReading, SensorReading.sensor_id == Sensor.id)
            .where(
                Sensor.machine_id == machine_id,
                SensorReading.recorded_at >= start,
                SensorReading.recorded_at < end,
            )
            .group_by(Sensor.id)
        )

        return [
            SensorFeatureAggregate(
                sensor_id=row.sensor_id,
                reading_count=row.reading_count,
                mean=float(row.mean),
                minimum=float(row.minimum),
                maximum=float(row.maximum),
                standard_deviation=float(row.standard_deviation),
                first_value=float(row.first_value),
                last_value=float(row.last_value),
                first_recorded_at=row.first_recorded_at,
                last_recorded_at=row.last_recorded_at,
                exceeding_reading_count=row.exceeding_reading_count,
            )
            for row in self.db.execute(statement)
        ]
