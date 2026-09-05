from datetime import UTC, datetime, timedelta
from math import sqrt
from uuid import UUID

import pytest
from app.core.enums import SensorType
from app.domain.predictive_features import (
    PREDICTIVE_FEATURE_VERSION,
    PredictiveFeatureConfigurationError,
    PredictiveFeatureDataError,
    PredictiveFeatureWindow,
    require_positive_finite_threshold,
)
from app.models import AlertThreshold, Machine, Sensor, SensorReading
from app.services.predictive_features import PredictiveFeatureService

FEATURE_END = datetime(2026, 8, 28, 12, tzinfo=UTC)


def _add_sensor(
    db,
    machine: Machine,
    *,
    name: str = "Temperature Sensor",
    sensor_type: SensorType = SensorType.TEMPERATURE,
    unit: str = "°C",
) -> Sensor:
    sensor = Sensor(
        machine_id=machine.id,
        name=name,
        sensor_type=sensor_type,
        unit=unit,
    )
    db.add(sensor)
    db.flush()
    return sensor


def _add_reading(
    db,
    sensor: Sensor,
    *,
    value: float,
    recorded_at: datetime,
    reading_id: UUID | None = None,
) -> SensorReading:
    reading = SensorReading(
        sensor_id=sensor.id,
        value=value,
        recorded_at=recorded_at,
    )
    if reading_id is not None:
        reading.id = reading_id
    db.add(reading)
    return reading


def _query(client, machine: Machine, **params):
    query = {"end": FEATURE_END.isoformat(), **params}
    return client.get(
        f"/api/v1/machines/{machine.id}/predictive-features",
        params=query,
    )


def test_unknown_machine_returns_404(client):
    response = client.get(
        f"/api/v1/machines/{UUID(int=0)}/predictive-features",
        params={"end": FEATURE_END.isoformat()},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Machine not found"}


def test_existing_machine_without_sensors_returns_empty_vector(client, test_machine):
    response = _query(client, test_machine)

    assert response.status_code == 200
    assert response.json() == {
        "feature_version": PREDICTIVE_FEATURE_VERSION,
        "machine_id": str(test_machine.id),
        "window": "24h",
        "window_start": "2026-08-27T12:00:00Z",
        "window_end": "2026-08-28T12:00:00Z",
        "sensor_features": [],
    }


def test_sensor_without_readings_returns_no_data_features(
    client,
    db,
    test_machine,
):
    sensor = _add_sensor(db, test_machine)

    response = _query(client, test_machine)

    assert response.status_code == 200
    feature = response.json()["sensor_features"][0]
    assert feature["sensor_id"] == str(sensor.id)
    assert feature["reading_count"] == 0
    assert feature["coverage_status"] == "NO_DATA"
    assert feature["time_span_seconds"] == 0
    assert feature["threshold_value"] == 90
    nullable_fields = {
        "mean",
        "minimum",
        "maximum",
        "standard_deviation",
        "first_value",
        "last_value",
        "absolute_change",
        "percent_change",
        "maximum_threshold_ratio",
        "mean_threshold_ratio",
        "exceeding_reading_fraction",
    }
    assert all(feature[field] is None for field in nullable_fields)
    assert feature["exceeding_reading_count"] == 0


def test_one_reading_returns_sparse_features(client, db, test_machine):
    sensor = _add_sensor(db, test_machine)
    _add_reading(
        db,
        sensor,
        value=72,
        recorded_at=FEATURE_END - timedelta(minutes=5),
    )
    db.flush()

    feature = _query(client, test_machine).json()["sensor_features"][0]

    assert feature["reading_count"] == 1
    assert feature["mean"] == 72
    assert feature["minimum"] == 72
    assert feature["maximum"] == 72
    assert feature["standard_deviation"] == 0
    assert feature["first_value"] == 72
    assert feature["last_value"] == 72
    assert feature["absolute_change"] == 0
    assert feature["percent_change"] == 0
    assert feature["time_span_seconds"] == 0
    assert feature["coverage_status"] == "SPARSE"


def test_multiple_readings_compute_statistical_threshold_and_change_features(
    client,
    db,
    test_machine,
):
    sensor = _add_sensor(db, test_machine)
    for minutes, value in [(50, 80), (40, 90), (30, 100), (20, 110), (10, 120)]:
        _add_reading(
            db,
            sensor,
            value=value,
            recorded_at=FEATURE_END - timedelta(minutes=minutes),
        )
    db.flush()

    feature = _query(client, test_machine, window="1h").json()["sensor_features"][0]

    assert feature["reading_count"] == 5
    assert feature["mean"] == 100
    assert feature["minimum"] == 80
    assert feature["maximum"] == 120
    assert feature["standard_deviation"] == pytest.approx(sqrt(200))
    assert feature["first_value"] == 80
    assert feature["last_value"] == 120
    assert feature["absolute_change"] == 40
    assert feature["percent_change"] == 50
    assert feature["threshold_value"] == 90
    assert feature["maximum_threshold_ratio"] == pytest.approx(120 / 90)
    assert feature["mean_threshold_ratio"] == pytest.approx(100 / 90)
    assert feature["exceeding_reading_count"] == 3
    assert feature["exceeding_reading_fraction"] == pytest.approx(3 / 5)
    assert feature["time_span_seconds"] == 40 * 60
    assert feature["coverage_status"] == "SUFFICIENT"


def test_same_timestamp_uses_id_for_deterministic_first_and_last(
    client,
    db,
    test_machine,
):
    sensor = _add_sensor(db, test_machine)
    timestamp = FEATURE_END - timedelta(minutes=5)
    _add_reading(db, sensor, value=10, recorded_at=timestamp, reading_id=UUID(int=1))
    _add_reading(db, sensor, value=20, recorded_at=timestamp, reading_id=UUID(int=2))
    db.flush()

    feature = _query(client, test_machine).json()["sensor_features"][0]

    assert feature["first_value"] == 10
    assert feature["last_value"] == 20
    assert feature["absolute_change"] == 10


def test_zero_first_value_makes_percent_change_null(client, db, test_machine):
    sensor = _add_sensor(db, test_machine)
    _add_reading(db, sensor, value=0, recorded_at=FEATURE_END - timedelta(minutes=2))
    _add_reading(db, sensor, value=5, recorded_at=FEATURE_END - timedelta(minutes=1))
    db.flush()

    feature = _query(client, test_machine).json()["sensor_features"][0]

    assert feature["absolute_change"] == 5
    assert feature["percent_change"] is None


def test_window_is_start_inclusive_and_end_exclusive(client, db, test_machine):
    sensor = _add_sensor(db, test_machine)
    start = FEATURE_END - timedelta(hours=1)
    for timestamp, value in [
        (start - timedelta(microseconds=1), 1),
        (start, 2),
        (FEATURE_END - timedelta(microseconds=1), 3),
        (FEATURE_END, 4),
    ]:
        _add_reading(db, sensor, value=value, recorded_at=timestamp)
    db.flush()

    feature = _query(client, test_machine, window="1h").json()["sensor_features"][0]

    assert feature["reading_count"] == 2
    assert feature["first_value"] == 2
    assert feature["last_value"] == 3


@pytest.mark.parametrize(
    ("end", "expected_end"),
    [
        ("2026-08-28T17:30:00+05:30", "2026-08-28T12:00:00Z"),
        ("2026-08-28T08:00:00-04:00", "2026-08-28T12:00:00Z"),
        ("2026-11-01T01:30:00-05:00", "2026-11-01T06:30:00Z"),
    ],
    ids=["positive-offset", "negative-offset", "dst-adjacent"],
)
def test_aware_end_offsets_normalize_to_utc(client, test_machine, end, expected_end):
    response = client.get(
        f"/api/v1/machines/{test_machine.id}/predictive-features",
        params={"end": end, "window": "1h"},
    )

    assert response.status_code == 200
    assert response.json()["window_end"] == expected_end


@pytest.mark.parametrize(
    ("window", "expected_start"),
    [
        ("1h", "2026-08-28T11:00:00Z"),
        ("6h", "2026-08-28T06:00:00Z"),
        ("24h", "2026-08-27T12:00:00Z"),
        ("7d", "2026-08-21T12:00:00Z"),
    ],
)
def test_supported_windows_have_exact_bounds(
    client,
    test_machine,
    window,
    expected_start,
):
    response = _query(client, test_machine, window=window)

    assert response.status_code == 200
    assert response.json()["window_start"] == expected_start
    assert response.json()["window_end"] == "2026-08-28T12:00:00Z"


def test_default_window_is_24_hours_and_feature_version_is_v1(client, test_machine):
    response = _query(client, test_machine)

    assert response.status_code == 200
    assert response.json()["window"] == "24h"
    assert response.json()["feature_version"] == "v1"


def test_omitted_end_is_computed_once_as_current_utc_time(client, test_machine):
    before = datetime.now(UTC)
    response = client.get(f"/api/v1/machines/{test_machine.id}/predictive-features")
    after = datetime.now(UTC)

    assert response.status_code == 200
    payload = response.json()
    window_end = datetime.fromisoformat(payload["window_end"].replace("Z", "+00:00"))
    window_start = datetime.fromisoformat(payload["window_start"].replace("Z", "+00:00"))
    assert before <= window_end <= after
    assert window_end - window_start == timedelta(hours=24)


@pytest.mark.parametrize(
    ("params", "expected_fragment"),
    [
        ({"window": "30d"}, "Input should be"),
        ({"end": "2026-08-28T12:00:00"}, "timezone"),
    ],
)
def test_invalid_window_or_naive_end_returns_422(
    client,
    test_machine,
    params,
    expected_fragment,
):
    response = client.get(
        f"/api/v1/machines/{test_machine.id}/predictive-features",
        params=params,
    )

    assert response.status_code == 422
    assert expected_fragment.lower() in str(response.json()).lower()


def test_threshold_is_persisted_configuration_and_equality_is_not_exceedance(
    client,
    db,
    test_machine,
):
    threshold = db.get(AlertThreshold, SensorType.TEMPERATURE)
    threshold.threshold_value = 75
    sensor = _add_sensor(db, test_machine)
    _add_reading(db, sensor, value=75, recorded_at=FEATURE_END - timedelta(minutes=2))
    _add_reading(db, sensor, value=76, recorded_at=FEATURE_END - timedelta(minutes=1))
    db.flush()

    feature = _query(client, test_machine).json()["sensor_features"][0]

    assert feature["threshold_value"] == 75
    assert feature["exceeding_reading_count"] == 1
    assert feature["exceeding_reading_fraction"] == 0.5


def test_missing_threshold_fails_explicitly(client, db, test_machine):
    _add_sensor(db, test_machine)
    threshold = db.get(AlertThreshold, SensorType.TEMPERATURE)
    db.delete(threshold)
    db.flush()

    response = _query(client, test_machine)

    assert response.status_code == 500
    assert response.json() == {"detail": "Missing persisted alert thresholds for: TEMPERATURE"}


@pytest.mark.parametrize("threshold", [0, -1, float("inf"), float("nan")])
def test_invalid_thresholds_fail_defensively(threshold):
    with pytest.raises(PredictiveFeatureConfigurationError):
        require_positive_finite_threshold(threshold)


def test_multiple_same_type_sensors_are_returned_in_deterministic_order(
    client,
    db,
    test_machine,
):
    second = _add_sensor(db, test_machine, name="Beta Sensor")
    first = _add_sensor(db, test_machine, name="Alpha Sensor")
    for sensor in [first, second]:
        _add_reading(
            db,
            sensor,
            value=70,
            recorded_at=FEATURE_END - timedelta(minutes=1),
        )
    db.flush()

    payload = _query(client, test_machine).json()
    features = payload["sensor_features"]

    assert [feature["sensor_name"] for feature in features] == [
        "Alpha Sensor",
        "Beta Sensor",
    ]
    assert all(feature["window_start"] == payload["window_start"] for feature in features)
    assert all(feature["window_end"] == payload["window_end"] for feature in features)
    assert {feature["sensor_id"] for feature in features} == {
        str(first.id),
        str(second.id),
    }


def test_response_contract_contains_features_not_predictions(client, db, test_machine):
    sensor = _add_sensor(db, test_machine)
    _add_reading(
        db,
        sensor,
        value=70,
        recorded_at=FEATURE_END - timedelta(minutes=1),
    )
    db.flush()

    payload = _query(client, test_machine).json()
    serialized = str(payload).lower()

    assert "prediction" not in serialized
    assert "probability" not in serialized
    assert "risk" not in serialized
    assert "nan" not in serialized
    assert "inf" not in serialized


def test_nonfinite_stored_telemetry_cannot_be_serialized(db, test_machine):
    sensor = _add_sensor(db, test_machine)
    _add_reading(
        db,
        sensor,
        value=float("nan"),
        recorded_at=FEATURE_END - timedelta(minutes=1),
    )
    db.flush()

    with pytest.raises(PredictiveFeatureDataError):
        PredictiveFeatureService(db).get_machine_features(
            machine_id=test_machine.id,
            window=PredictiveFeatureWindow.TWENTY_FOUR_HOURS,
            end=FEATURE_END,
        )
