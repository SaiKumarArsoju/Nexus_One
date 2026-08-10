import random
from datetime import UTC, datetime, timedelta

from app.core.enums import SensorType
from app.database.session import SessionLocal
from app.models import Sensor, SensorReading
from sqlalchemy import select

READINGS_PER_SENSOR = 100


def generate_value(sensor_type: SensorType) -> float:
    if sensor_type == SensorType.TEMPERATURE:
        return round(random.uniform(65.0, 95.0), 2)

    if sensor_type == SensorType.PRESSURE:
        return round(random.uniform(4.0, 8.0), 2)

    if sensor_type == SensorType.VIBRATION:
        return round(random.uniform(0.05, 0.5), 3)

    if sensor_type == SensorType.RPM:
        return round(random.uniform(1200.0, 3000.0), 0)

    if sensor_type == SensorType.ENERGY:
        return round(random.uniform(10.0, 30.0), 2)

    raise ValueError(f"Unsupported sensor type: {sensor_type}")


def generate_telemetry() -> None:
    with SessionLocal() as db:
        sensors = db.scalars(select(Sensor)).all()

        if not sensors:
            print("No sensors found. Run the seed script first.")
            return

        now = datetime.now(UTC)
        readings = []

        for sensor in sensors:
            for reading_index in range(READINGS_PER_SENSOR):
                recorded_at = now - timedelta(minutes=READINGS_PER_SENSOR - reading_index)

                readings.append(
                    SensorReading(
                        sensor_id=sensor.id,
                        value=generate_value(sensor.sensor_type),
                        recorded_at=recorded_at,
                    )
                )

        db.add_all(readings)
        db.commit()

        print("Telemetry generation completed.")
        print(f"Sensors processed: {len(sensors)}")
        print(f"Readings per sensor: {READINGS_PER_SENSOR}")
        print(f"Total readings created: {len(readings)}")


if __name__ == "__main__":
    generate_telemetry()
