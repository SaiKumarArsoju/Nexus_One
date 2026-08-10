from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas import DashboardSummaryResponse
from app.services import DashboardService

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
)
def get_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardSummaryResponse:
    return DashboardService(db).get_summary()
