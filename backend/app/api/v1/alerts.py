from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import AlertResponse
from app.services import AlertService

router = APIRouter(prefix="/api/v1", tags=["Alerts"])


@router.get(
    "/alerts",
    response_model=list[AlertResponse],
)
def get_active_alerts(
    db: Annotated[Session, Depends(get_db)],
) -> list[AlertResponse]:
    return AlertService(db).get_active_alerts()


@router.post("/alerts/sync")
def sync_alerts(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    created = AlertService(db).sync_machine_alerts()

    return {
        "created_alerts": created,
    }
