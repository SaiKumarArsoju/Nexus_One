from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.alert_rules import AlertThresholdConfigurationError
from app.domain.predictive_features import (
    PREDICTIVE_FEATURE_VERSION,
    PREDICTIVE_FEATURE_WINDOW_DURATIONS,
    PredictiveFeatureWindow,
    classify_coverage,
    require_finite,
    require_positive_finite_threshold,
    safe_percent_change,
)
from app.models import Sensor
from app.repositories.alert_threshold import AlertThresholdRepository
from app.repositories.predictive_features import (
    PredictiveFeatureRepository,
    SensorFeatureAggregate,
)
from app.schemas.predictive import (
    MachinePredictiveFeaturesResponse,
    SensorPredictiveFeatureResponse,
)


class PredictiveFeatureService:
    def __init__(self, db: Session) -> None:
        self.repository = PredictiveFeatureRepository(db)
        self.threshold_repository = AlertThresholdRepository(db)

    def get_machine_features(
        self,
        *,
        machine_id: UUID,
        window: PredictiveFeatureWindow = PredictiveFeatureWindow.TWENTY_FOUR_HOURS,
        end: datetime | None = None,
    ) -> MachinePredictiveFeaturesResponse:
        if self.repository.get_machine(machine_id) is None:
            raise LookupError("Machine not found")

        window_end = self._normalize_end(end)
        window_start = window_end - PREDICTIVE_FEATURE_WINDOW_DURATIONS[window]
        sensors = self.repository.list_machine_sensors(machine_id)
        thresholds = self.threshold_repository.get_threshold_map()

        missing_types = sorted(
            {sensor.sensor_type for sensor in sensors if sensor.sensor_type not in thresholds},
            key=lambda sensor_type: sensor_type.value,
        )
        if missing_types:
            values = ", ".join(sensor_type.value for sensor_type in missing_types)
            raise AlertThresholdConfigurationError(
                f"Missing persisted alert thresholds for: {values}"
            )

        validated_thresholds = {
            sensor_type: require_positive_finite_threshold(value)
            for sensor_type, value in thresholds.items()
        }
        aggregates = {
            row.sensor_id: row
            for row in self.repository.aggregate_machine_sensor_features(
                machine_id=machine_id,
                start=window_start,
                end=window_end,
                thresholds=validated_thresholds,
            )
        }

        return MachinePredictiveFeaturesResponse(
            feature_version=PREDICTIVE_FEATURE_VERSION,
            machine_id=machine_id,
            window=window,
            window_start=window_start,
            window_end=window_end,
            sensor_features=[
                self._build_sensor_features(
                    sensor=sensor,
                    aggregate=aggregates.get(sensor.id),
                    threshold=validated_thresholds[sensor.sensor_type],
                    window_start=window_start,
                    window_end=window_end,
                )
                for sensor in sensors
            ],
        )

    @staticmethod
    def _normalize_end(end: datetime | None) -> datetime:
        if end is None:
            return datetime.now(UTC)
        if end.utcoffset() is None:
            raise ValueError("end must include a timezone")
        return end.astimezone(UTC)

    @staticmethod
    def _build_sensor_features(
        *,
        sensor: Sensor,
        aggregate: SensorFeatureAggregate | None,
        threshold: float,
        window_start: datetime,
        window_end: datetime,
    ) -> SensorPredictiveFeatureResponse:
        if aggregate is None:
            return SensorPredictiveFeatureResponse(
                sensor_id=sensor.id,
                sensor_name=sensor.name,
                sensor_type=sensor.sensor_type,
                unit=sensor.unit,
                window_start=window_start,
                window_end=window_end,
                reading_count=0,
                mean=None,
                minimum=None,
                maximum=None,
                standard_deviation=None,
                first_value=None,
                last_value=None,
                absolute_change=None,
                percent_change=None,
                threshold_value=threshold,
                maximum_threshold_ratio=None,
                mean_threshold_ratio=None,
                exceeding_reading_count=0,
                exceeding_reading_fraction=None,
                time_span_seconds=0,
                coverage_status=classify_coverage(0),
            )

        mean = require_finite(aggregate.mean, feature_name="mean")
        minimum = require_finite(aggregate.minimum, feature_name="minimum")
        maximum = require_finite(aggregate.maximum, feature_name="maximum")
        stddev = require_finite(
            aggregate.standard_deviation,
            feature_name="standard deviation",
        )
        first_value = require_finite(aggregate.first_value, feature_name="first value")
        last_value = require_finite(aggregate.last_value, feature_name="last value")
        assert mean is not None and maximum is not None
        assert first_value is not None and last_value is not None
        absolute_change = require_finite(
            last_value - first_value,
            feature_name="absolute change",
        )
        percent_change = require_finite(
            safe_percent_change(first_value, last_value),
            feature_name="percent change",
        )

        return SensorPredictiveFeatureResponse(
            sensor_id=sensor.id,
            sensor_name=sensor.name,
            sensor_type=sensor.sensor_type,
            unit=sensor.unit,
            window_start=window_start,
            window_end=window_end,
            reading_count=aggregate.reading_count,
            mean=mean,
            minimum=minimum,
            maximum=maximum,
            standard_deviation=stddev,
            first_value=first_value,
            last_value=last_value,
            absolute_change=absolute_change,
            percent_change=percent_change,
            threshold_value=threshold,
            maximum_threshold_ratio=require_finite(
                maximum / threshold,
                feature_name="maximum threshold ratio",
            ),
            mean_threshold_ratio=require_finite(
                mean / threshold,
                feature_name="mean threshold ratio",
            ),
            exceeding_reading_count=aggregate.exceeding_reading_count,
            exceeding_reading_fraction=require_finite(
                aggregate.exceeding_reading_count / aggregate.reading_count,
                feature_name="exceeding reading fraction",
            ),
            time_span_seconds=(
                aggregate.last_recorded_at - aggregate.first_recorded_at
            ).total_seconds(),
            coverage_status=classify_coverage(aggregate.reading_count),
        )
