from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import SensorType
from app.database.session import get_db
from app.domain.alert_rules import AlertThresholdConfigurationError
from app.schemas import AlertThresholdResponse, AlertThresholdUpdate
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


@router.put(
    "/alert-thresholds/{sensor_type}",
    response_model=AlertThresholdResponse,
)
def update_alert_threshold(
    sensor_type: SensorType,
    update: AlertThresholdUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> AlertThresholdResponse:
    try:
        return AlertThresholdService(db).update_alert_threshold(
            sensor_type=sensor_type,
            threshold_value=update.threshold_value,
        )
    except AlertThresholdConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
