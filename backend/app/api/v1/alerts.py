from typing import Annotated
from uuid import UUID

from anyio import from_thread
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.realtime import publish_committed_events
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


@router.get(
    "/alerts/history",
    response_model=list[AlertResponse],
)
def get_alert_history(
    db: Annotated[Session, Depends(get_db)],
) -> list[AlertResponse]:
    return AlertService(db).get_alert_history()


@router.patch(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertResponse,
)
def acknowledge_alert(
    alert_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> AlertResponse:
    try:
        operation = AlertService(db).acknowledge_alert_operation(alert_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    from_thread.run(publish_committed_events, operation.events)

    return operation.result


@router.patch(
    "/alerts/{alert_id}/resolve",
    response_model=AlertResponse,
)
def resolve_alert(
    alert_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> AlertResponse:
    try:
        operation = AlertService(db).resolve_alert_operation(alert_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    from_thread.run(publish_committed_events, operation.events)

    return operation.result


@router.post("/alerts/sync")
def sync_alerts(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    operation = AlertService(db).sync_machine_alerts_operation()
    from_thread.run(publish_committed_events, operation.events)

    return {
        "created_alerts": operation.result,
    }
