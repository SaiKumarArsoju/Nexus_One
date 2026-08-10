from pydantic import BaseModel


class MachineHealthResponse(BaseModel):
    machine_name: str
    status: str
    overall_health: int
    temperature: float | None = None
    pressure: float | None = None
    vibration: float | None = None
    rpm: float | None = None
    energy: float | None = None
    warnings: list[str]
    recommendation: str
