from fastapi import FastAPI

app = FastAPI(
    title="NEXUS ONE API",
    description="Enterprise Operations Intelligence Platform",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to NEXUS ONE",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "nexus-one-backend",
    }