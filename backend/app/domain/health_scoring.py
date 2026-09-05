from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from uuid import UUID

from app.domain.predictive_features import FeatureCoverageStatus

HEALTH_SCORING_VERSION = "v1"
MACHINE_AVERAGE_WEIGHT = 0.7
MACHINE_MINIMUM_WEIGHT = 0.3
MAX_SENSOR_REASONS = 5

MAXIMUM_RATIO_PENALTY_CAP = 30.0
MEAN_RATIO_PENALTY_CAP = 15.0
EXCEEDANCE_PENALTY_CAP = 35.0
TREND_PENALTY_CAP = 10.0
VARIABILITY_PENALTY_CAP = 10.0


class HealthBand(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    ATTENTION = "ATTENTION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class HealthConfidence(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class HealthScoringDataError(RuntimeError):
    """Raised when a feature vector cannot produce finite scoring output."""


@dataclass(frozen=True)
class SensorScoringInput:
    sensor_id: UUID
    reading_count: int
    coverage_status: FeatureCoverageStatus
    threshold_value: float
    maximum_threshold_ratio: float | None
    mean_threshold_ratio: float | None
    exceeding_reading_fraction: float | None
    percent_change: float | None
    standard_deviation: float | None


@dataclass(frozen=True)
class SensorPenaltyResult:
    threshold_proximity: float
    mean_level: float
    exceedance: float
    trend: float
    variability: float

    @property
    def total(self) -> float:
        return (
            self.threshold_proximity
            + self.mean_level
            + self.exceedance
            + self.trend
            + self.variability
        )


@dataclass(frozen=True)
class SensorScoreResult:
    health_score: float | None
    health_band: HealthBand
    confidence: HealthConfidence
    penalties: SensorPenaltyResult
    reasons: tuple[str, ...]


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(value, maximum))


def classify_health_band(score: float | None) -> HealthBand:
    if score is None:
        return HealthBand.INSUFFICIENT_DATA
    if score >= 80:
        return HealthBand.HEALTHY
    if score >= 60:
        return HealthBand.WATCH
    return HealthBand.ATTENTION


def sensor_confidence(coverage: FeatureCoverageStatus) -> HealthConfidence:
    if coverage == FeatureCoverageStatus.NO_DATA:
        return HealthConfidence.NONE
    if coverage == FeatureCoverageStatus.SPARSE:
        return HealthConfidence.LOW
    return HealthConfidence.HIGH


def threshold_proximity_penalty(ratio: float) -> float:
    _require_finite(ratio, "maximum threshold ratio")
    if ratio <= 0.8:
        return 0
    if ratio <= 1:
        return (ratio - 0.8) / 0.2 * 10
    return 10 + min(
        (ratio - 1) / 0.5 * (MAXIMUM_RATIO_PENALTY_CAP - 10),
        MAXIMUM_RATIO_PENALTY_CAP - 10,
    )


def mean_level_penalty(ratio: float) -> float:
    _require_finite(ratio, "mean threshold ratio")
    if ratio <= 0.7:
        return 0
    if ratio <= 1:
        return (ratio - 0.7) / 0.3 * 7.5
    return 7.5 + min(
        (ratio - 1) / 0.5 * (MEAN_RATIO_PENALTY_CAP - 7.5),
        MEAN_RATIO_PENALTY_CAP - 7.5,
    )


def exceedance_penalty(fraction: float) -> float:
    _require_finite(fraction, "exceeding reading fraction")
    if not 0 <= fraction <= 1:
        raise HealthScoringDataError("Exceeding reading fraction must be between 0 and 1")
    return fraction * EXCEEDANCE_PENALTY_CAP


def trend_penalty(percent_change: float | None) -> float:
    if percent_change is None:
        return 0
    _require_finite(percent_change, "percent change")
    magnitude = abs(percent_change)
    if magnitude <= 5:
        return 0
    return min((magnitude - 5) / 45 * TREND_PENALTY_CAP, TREND_PENALTY_CAP)


def variability_penalty(standard_deviation: float, threshold_value: float) -> float:
    _require_finite(standard_deviation, "standard deviation")
    _require_finite(threshold_value, "threshold")
    if threshold_value <= 0:
        raise HealthScoringDataError("Threshold must be positive for scoring")
    ratio = standard_deviation / threshold_value
    if ratio <= 0.05:
        return 0
    return min((ratio - 0.05) / 0.2 * VARIABILITY_PENALTY_CAP, VARIABILITY_PENALTY_CAP)


def score_sensor(features: SensorScoringInput) -> SensorScoreResult:
    empty_penalties = SensorPenaltyResult(0, 0, 0, 0, 0)
    confidence = sensor_confidence(features.coverage_status)
    if features.coverage_status == FeatureCoverageStatus.NO_DATA:
        return SensorScoreResult(
            health_score=None,
            health_band=HealthBand.INSUFFICIENT_DATA,
            confidence=confidence,
            penalties=empty_penalties,
            reasons=("No readings available in the selected window.",),
        )

    required = (
        features.maximum_threshold_ratio,
        features.mean_threshold_ratio,
        features.exceeding_reading_fraction,
        features.standard_deviation,
    )
    if any(value is None for value in required):
        raise HealthScoringDataError("Scorable sensor features are incomplete")
    maximum_ratio, mean_ratio, exceeding_fraction, standard_deviation = required
    assert maximum_ratio is not None
    assert mean_ratio is not None
    assert exceeding_fraction is not None
    assert standard_deviation is not None

    penalties = SensorPenaltyResult(
        threshold_proximity=threshold_proximity_penalty(maximum_ratio),
        mean_level=mean_level_penalty(mean_ratio),
        exceedance=exceedance_penalty(exceeding_fraction),
        trend=trend_penalty(features.percent_change),
        variability=variability_penalty(
            standard_deviation,
            features.threshold_value,
        ),
    )
    score = _rounded(clamp(100 - penalties.total))
    reasons = _sensor_reasons(features, penalties)

    return SensorScoreResult(
        health_score=score,
        health_band=classify_health_band(score),
        confidence=confidence,
        penalties=SensorPenaltyResult(
            threshold_proximity=_rounded(penalties.threshold_proximity),
            mean_level=_rounded(penalties.mean_level),
            exceedance=_rounded(penalties.exceedance),
            trend=_rounded(penalties.trend),
            variability=_rounded(penalties.variability),
        ),
        reasons=reasons,
    )


def machine_confidence(
    sensor_coverages: list[FeatureCoverageStatus],
) -> HealthConfidence:
    scored = [status for status in sensor_coverages if status != FeatureCoverageStatus.NO_DATA]
    if not scored:
        return HealthConfidence.NONE
    if all(status == FeatureCoverageStatus.SPARSE for status in scored):
        return HealthConfidence.LOW
    if len(scored) == len(sensor_coverages) and all(
        status == FeatureCoverageStatus.SUFFICIENT for status in scored
    ):
        return HealthConfidence.HIGH
    return HealthConfidence.MEDIUM


def aggregate_machine_score(sensor_scores: list[float]) -> float | None:
    if not sensor_scores:
        return None
    for score in sensor_scores:
        _require_finite(score, "sensor health score")
    average = sum(sensor_scores) / len(sensor_scores)
    minimum = min(sensor_scores)
    return _rounded(clamp(MACHINE_AVERAGE_WEIGHT * average + MACHINE_MINIMUM_WEIGHT * minimum))


def _sensor_reasons(
    features: SensorScoringInput,
    penalties: SensorPenaltyResult,
) -> tuple[str, ...]:
    candidates = [
        (
            penalties.exceedance,
            0,
            (
                f"{features.exceeding_reading_fraction * 100:.1f}% of readings "
                "exceeded the configured threshold."
            ),
        ),
        (
            penalties.threshold_proximity,
            1,
            (
                f"Maximum reached {features.maximum_threshold_ratio * 100:.1f}% "
                "of the configured threshold."
            ),
        ),
        (
            penalties.mean_level,
            2,
            f"Mean reached {features.mean_threshold_ratio * 100:.1f}% of the configured threshold.",
        ),
        (
            penalties.trend,
            3,
            f"Telemetry changed {abs(features.percent_change or 0):.1f}% across the window.",
        ),
        (
            penalties.variability,
            4,
            "Variability was elevated relative to the configured threshold.",
        ),
    ]
    reasons = [
        reason
        for penalty, _, reason in sorted(candidates, key=lambda item: (-item[0], item[1]))
        if penalty > 0
    ]
    if features.coverage_status == FeatureCoverageStatus.SPARSE:
        reasons.append(f"Only {features.reading_count} readings were available; confidence is low.")
    if not reasons:
        reasons.append("Telemetry remained comfortably within configured limits.")
    return tuple(reasons[:MAX_SENSOR_REASONS])


def _require_finite(value: float, name: str) -> None:
    if not isfinite(value):
        raise HealthScoringDataError(f"Non-finite {name}")


def _rounded(value: float) -> float:
    _require_finite(value, "scoring result")
    return round(value, 1)
