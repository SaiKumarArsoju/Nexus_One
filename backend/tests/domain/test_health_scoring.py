from uuid import UUID

import pytest
from app.domain.health_scoring import (
    HealthBand,
    HealthConfidence,
    HealthScoringDataError,
    SensorScoringInput,
    aggregate_machine_score,
    classify_health_band,
    exceedance_penalty,
    machine_confidence,
    mean_level_penalty,
    score_sensor,
    threshold_proximity_penalty,
    trend_penalty,
    variability_penalty,
)
from app.domain.predictive_features import FeatureCoverageStatus


def _features(
    *,
    reading_count=10,
    coverage=FeatureCoverageStatus.SUFFICIENT,
    maximum_ratio=0.7,
    mean_ratio=0.6,
    exceedance_fraction=0,
    percent_change=0,
    standard_deviation=2,
    threshold=100,
) -> SensorScoringInput:
    return SensorScoringInput(
        sensor_id=UUID(int=1),
        reading_count=reading_count,
        coverage_status=coverage,
        threshold_value=threshold,
        maximum_threshold_ratio=maximum_ratio,
        mean_threshold_ratio=mean_ratio,
        exceeding_reading_fraction=exceedance_fraction,
        percent_change=percent_change,
        standard_deviation=standard_deviation,
    )


def test_threshold_proximity_penalty_is_piecewise_and_bounded():
    assert threshold_proximity_penalty(0.8) == 0
    assert threshold_proximity_penalty(0.9) == pytest.approx(5)
    assert threshold_proximity_penalty(1) == pytest.approx(10)
    assert threshold_proximity_penalty(1.25) == pytest.approx(20)
    assert threshold_proximity_penalty(10) == 30


def test_mean_level_penalty_is_lower_weight_and_bounded():
    assert mean_level_penalty(0.7) == 0
    assert mean_level_penalty(0.85) == pytest.approx(3.75)
    assert mean_level_penalty(1) == pytest.approx(7.5)
    assert mean_level_penalty(10) == 15


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [(0, 0), (0.1, 3.5), (1, 35)],
)
def test_exceedance_penalty_is_linear_and_bounded(fraction, expected):
    assert exceedance_penalty(fraction) == expected


def test_invalid_exceedance_fraction_fails_explicitly():
    with pytest.raises(HealthScoringDataError):
        exceedance_penalty(1.01)


def test_trend_penalty_uses_absolute_magnitude_and_is_bounded():
    assert trend_penalty(None) == 0
    assert trend_penalty(5) == 0
    assert trend_penalty(-27.5) == pytest.approx(5)
    assert trend_penalty(500) == 10


def test_variability_penalty_is_threshold_normalized_and_bounded():
    assert variability_penalty(5, 100) == 0
    assert variability_penalty(15, 100) == pytest.approx(5)
    assert variability_penalty(100, 100) == 10


def test_variability_does_not_depend_on_mean_and_rejects_zero_threshold():
    assert variability_penalty(10, 100) == pytest.approx(2.5)
    with pytest.raises(HealthScoringDataError):
        variability_penalty(10, 0)


def test_no_data_sensor_has_null_score_and_no_confidence():
    result = score_sensor(
        _features(
            reading_count=0,
            coverage=FeatureCoverageStatus.NO_DATA,
            maximum_ratio=None,
            mean_ratio=None,
            exceedance_fraction=None,
            percent_change=None,
            standard_deviation=None,
        )
    )

    assert result.health_score is None
    assert result.health_band == HealthBand.INSUFFICIENT_DATA
    assert result.confidence == HealthConfidence.NONE
    assert result.penalties.total == 0
    assert result.reasons == ("No readings available in the selected window.",)


def test_sparse_sensor_is_scored_with_low_confidence():
    result = score_sensor(_features(reading_count=3, coverage=FeatureCoverageStatus.SPARSE))

    assert result.health_score == 100
    assert result.confidence == HealthConfidence.LOW
    assert result.reasons[-1] == "Only 3 readings were available; confidence is low."


def test_sufficient_sensor_has_high_confidence():
    assert score_sensor(_features()).confidence == HealthConfidence.HIGH


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (80, HealthBand.HEALTHY),
        (79.9, HealthBand.WATCH),
        (60, HealthBand.WATCH),
        (59.9, HealthBand.ATTENTION),
        (None, HealthBand.INSUFFICIENT_DATA),
    ],
)
def test_health_band_boundaries(score, band):
    assert classify_health_band(score) == band


def test_total_penalty_clamps_sensor_score_at_zero():
    result = score_sensor(
        _features(
            maximum_ratio=10,
            mean_ratio=10,
            exceedance_fraction=1,
            percent_change=500,
            standard_deviation=100,
        )
    )

    assert result.penalties.total == 100
    assert result.health_score == 0


def test_reasons_are_deterministic_prioritized_and_bounded():
    features = _features(
        reading_count=3,
        coverage=FeatureCoverageStatus.SPARSE,
        maximum_ratio=1.5,
        mean_ratio=1.5,
        exceedance_fraction=1,
        percent_change=100,
        standard_deviation=100,
    )

    first = score_sensor(features)
    second = score_sensor(features)

    assert first.reasons == second.reasons
    assert len(first.reasons) == 5
    assert first.reasons[0].startswith("100.0% of readings exceeded")


def test_evaluation_fixtures_are_monotonic_and_descriptive():
    healthy = score_sensor(_features())
    near = score_sensor(_features(maximum_ratio=0.95, mean_ratio=0.9))
    intermittent = score_sensor(
        _features(maximum_ratio=1.1, mean_ratio=0.95, exceedance_fraction=0.2)
    )
    sustained = score_sensor(_features(maximum_ratio=1.2, mean_ratio=1.1, exceedance_fraction=1))
    variable = score_sensor(_features(standard_deviation=25))
    sparse = score_sensor(_features(reading_count=3, coverage=FeatureCoverageStatus.SPARSE))

    assert healthy.health_score == 100
    assert near.health_score == 87.5
    assert intermittent.health_score == 72.8
    assert sustained.health_score == 38
    assert variable.health_score == 90
    assert sparse.health_score == healthy.health_score
    assert sparse.confidence == HealthConfidence.LOW
    assert (
        healthy.health_score
        > near.health_score
        > intermittent.health_score
        > sustained.health_score
    )


def test_machine_score_uses_seventy_thirty_average_minimum_blend():
    assert aggregate_machine_score([100, 80, 40]) == 63.3
    assert aggregate_machine_score([]) is None


@pytest.mark.parametrize(
    ("coverages", "expected"),
    [
        ([], HealthConfidence.NONE),
        ([FeatureCoverageStatus.NO_DATA], HealthConfidence.NONE),
        ([FeatureCoverageStatus.SPARSE], HealthConfidence.LOW),
        (
            [FeatureCoverageStatus.SUFFICIENT, FeatureCoverageStatus.NO_DATA],
            HealthConfidence.MEDIUM,
        ),
        (
            [FeatureCoverageStatus.SUFFICIENT, FeatureCoverageStatus.SPARSE],
            HealthConfidence.MEDIUM,
        ),
        (
            [FeatureCoverageStatus.SUFFICIENT, FeatureCoverageStatus.SUFFICIENT],
            HealthConfidence.HIGH,
        ),
    ],
)
def test_machine_confidence_policy(coverages, expected):
    assert machine_confidence(coverages) == expected


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_scoring_inputs_fail(value):
    with pytest.raises(HealthScoringDataError):
        threshold_proximity_penalty(value)
