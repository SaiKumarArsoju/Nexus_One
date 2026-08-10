from dataclasses import dataclass

from app.core.enums import SensorType


@dataclass(frozen=True)
class MachineHealthResult:
    status: str
    score: int


def calculate_machine_health(
    values: dict[SensorType, float],
) -> MachineHealthResult:
    score = 100

    temperature = values.get(SensorType.TEMPERATURE)
    pressure = values.get(SensorType.PRESSURE)
    vibration = values.get(SensorType.VIBRATION)
    rpm = values.get(SensorType.RPM)
    energy = values.get(SensorType.ENERGY)

    if temperature is not None and temperature > 90:
        score -= 20

    if pressure is not None and pressure > 7.5:
        score -= 15

    if vibration is not None and vibration > 0.4:
        score -= 25

    if rpm is not None and rpm > 2800:
        score -= 15

    if energy is not None and energy > 28:
        score -= 10

    score = max(score, 0)

    if score >= 85:
        status = "HEALTHY"
    elif score >= 60:
        status = "WARNING"
    else:
        status = "CRITICAL"

    return MachineHealthResult(
        status=status,
        score=score,
    )
