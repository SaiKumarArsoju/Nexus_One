from collections.abc import Mapping
from dataclasses import dataclass

from app.core.enums import SensorType
from app.domain.alert_rules import get_abnormal_alert_rules


@dataclass(frozen=True)
class MachineHealthResult:
    status: str
    score: int


def calculate_machine_health(
    values: Mapping[SensorType, float],
    thresholds: Mapping[SensorType, float],
) -> MachineHealthResult:
    abnormal_rules = get_abnormal_alert_rules(values, thresholds)
    score = max(
        100 - sum(rule.health_score_penalty for rule in abnormal_rules),
        0,
    )

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
