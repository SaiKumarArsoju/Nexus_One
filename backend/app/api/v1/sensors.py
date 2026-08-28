from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import SensorDiscoveryResponse
from app.services import SensorService

router = APIRouter(prefix="/api/v1", tags=["Sensors"])


@router.get(
    "/sensors",
    response_model=list[SensorDiscoveryResponse],
)
def get_sensors(
    db: Annotated[Session, Depends(get_db)],
) -> list[SensorDiscoveryResponse]:
    return SensorService(db).get_sensors()
