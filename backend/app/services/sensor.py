from sqlalchemy.orm import Session

from app.repositories import SensorRepository
from app.schemas import SensorDiscoveryResponse


class SensorService:
    def __init__(self, db: Session) -> None:
        self.repository = SensorRepository(db)

    def get_sensors(self) -> list[SensorDiscoveryResponse]:
        sensors = self.repository.get_all_sensors()

        return [
            SensorDiscoveryResponse(
                id=sensor.id,
                name=sensor.name,
                sensor_type=sensor.sensor_type,
                unit=sensor.unit,
                machine_id=sensor.machine_id,
            )
            for sensor in sensors
        ]
