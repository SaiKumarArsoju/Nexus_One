from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.health_scoring import (
    HEALTH_SCORING_VERSION,
    HealthConfidence,
    SensorScoringInput,
    aggregate_machine_score,
    classify_health_band,
    machine_confidence,
    score_sensor,
)
from app.domain.predictive_features import PredictiveFeatureWindow
from app.schemas.health import (
    MachineHealthScoreResponse,
    SensorHealthPenaltyResponse,
    SensorHealthScoreResponse,
)
from app.schemas.predictive import SensorPredictiveFeatureResponse
from app.services.predictive_features import PredictiveFeatureService

HEALTH_INDICATOR_TYPE = "DETERMINISTIC_MAINTENANCE_HEALTH_INDICATOR"


class HealthScoringService:
    def __init__(self, db: Session) -> None:
        self.feature_service = PredictiveFeatureService(db)

    def get_machine_health_score(
        self,
        *,
        machine_id: UUID,
        window: PredictiveFeatureWindow = PredictiveFeatureWindow.TWENTY_FOUR_HOURS,
        end: datetime | None = None,
    ) -> MachineHealthScoreResponse:
        features = self.feature_service.get_machine_features(
            machine_id=machine_id,
            window=window,
            end=end,
        )
        sensor_scores = [self._score_sensor(sensor) for sensor in features.sensor_features]
        scored = [score for score in sensor_scores if score.health_score is not None]
        numeric_scores = [score.health_score for score in scored]
        assert all(score is not None for score in numeric_scores)
        machine_score = aggregate_machine_score(
            [score for score in numeric_scores if score is not None]
        )
        confidence = machine_confidence(
            [sensor.coverage_status for sensor in features.sensor_features]
        )
        most_concerning = min(
            scored,
            key=lambda score: (score.health_score, str(score.sensor_id)),
            default=None,
        )

        return MachineHealthScoreResponse(
            indicator_type=HEALTH_INDICATOR_TYPE,
            feature_version=features.feature_version,
            scoring_version=HEALTH_SCORING_VERSION,
            machine_id=features.machine_id,
            window=features.window,
            window_start=features.window_start,
            window_end=features.window_end,
            health_score=machine_score,
            health_band=classify_health_band(machine_score),
            confidence=confidence,
            scored_sensor_count=len(scored),
            total_sensor_count=len(sensor_scores),
            most_concerning_sensor_id=(most_concerning.sensor_id if most_concerning else None),
            lowest_sensor_score=(most_concerning.health_score if most_concerning else None),
            sensor_scores=sensor_scores,
            reasons=self._machine_reasons(
                sensor_scores=sensor_scores,
                confidence=confidence,
                most_concerning=most_concerning,
            ),
        )

    @staticmethod
    def _score_sensor(
        features: SensorPredictiveFeatureResponse,
    ) -> SensorHealthScoreResponse:
        result = score_sensor(
            SensorScoringInput(
                sensor_id=features.sensor_id,
                reading_count=features.reading_count,
                coverage_status=features.coverage_status,
                threshold_value=features.threshold_value,
                maximum_threshold_ratio=features.maximum_threshold_ratio,
                mean_threshold_ratio=features.mean_threshold_ratio,
                exceeding_reading_fraction=features.exceeding_reading_fraction,
                percent_change=features.percent_change,
                standard_deviation=features.standard_deviation,
            )
        )
        return SensorHealthScoreResponse(
            sensor_id=features.sensor_id,
            sensor_name=features.sensor_name,
            sensor_type=features.sensor_type,
            unit=features.unit,
            health_score=result.health_score,
            health_band=result.health_band,
            confidence=result.confidence,
            threshold_value=features.threshold_value,
            component_penalties=SensorHealthPenaltyResponse(
                threshold_proximity=result.penalties.threshold_proximity,
                mean_level=result.penalties.mean_level,
                exceedance=result.penalties.exceedance,
                trend=result.penalties.trend,
                variability=result.penalties.variability,
            ),
            reasons=list(result.reasons),
            coverage_status=features.coverage_status,
        )

    @staticmethod
    def _machine_reasons(
        *,
        sensor_scores: list[SensorHealthScoreResponse],
        confidence: HealthConfidence,
        most_concerning: SensorHealthScoreResponse | None,
    ) -> list[str]:
        if not sensor_scores:
            return ["No sensors are configured for this machine."]

        reasons: list[str] = []
        exceeding = sum(score.component_penalties.exceedance > 0 for score in sensor_scores)
        no_data = sum(score.health_score is None for score in sensor_scores)
        if exceeding:
            reasons.append(
                f"{exceeding} of {len(sensor_scores)} sensors had readings above "
                "configured thresholds."
            )
        if most_concerning is not None:
            reasons.append(f"{most_concerning.sensor_name} has the lowest health score.")
        if no_data:
            reasons.append(
                f"{no_data} sensor{'s have' if no_data != 1 else ' has'} no telemetry "
                "in the selected window."
            )
        reasons.append(f"Overall data confidence is {confidence.value.lower()}.")
        return reasons
