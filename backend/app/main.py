from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.telemetry import router as telemetry_router
from app.core.config import settings
from app.database.session import get_db

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
)
app.include_router(telemetry_router)
app.include_router(health_router)
app.include_router(dashboard_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "status": "running",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check(
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    database_name, database_user = db.execute(text("SELECT current_database(), current_user")).one()

    return {
        "status": "healthy",
        "service": "nexus-one-backend",
        "environment": settings.environment,
        "database": database_name,
        "database_user": database_user,
    }
