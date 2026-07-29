from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "status": "running",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "nexus-one-backend",
        "environment": settings.environment,
    }
