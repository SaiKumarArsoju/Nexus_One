from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import AlertThresholdResponse
from app.services import AlertThresholdService

router = APIRouter(prefix="/api/v1", tags=["Alert Thresholds"])


@router.get(
    "/alert-thresholds",
    response_model=list[AlertThresholdResponse],
)
def get_alert_thresholds(
    db: Annotated[Session, Depends(get_db)],
) -> list[AlertThresholdResponse]:
    return AlertThresholdService(db).get_alert_thresholds()
