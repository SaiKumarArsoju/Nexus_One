from datetime import UTC, datetime, timedelta
from math import isfinite
from uuid import UUID

import pytest
from app.core.enums import SensorType
from app.models import AlertThreshold, Machine, Sensor, SensorReading

SCORE_END = datetime(2026, 8, 28, 12, tzinfo=UTC)


def _add_sensor(
    db,
    machine: Machine,
    *,
    name: str,
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


def _add_values(db, sensor: Sensor, values: list[float]) -> None:
    for index, value in enumerate(values, start=1):
        db.add(
            SensorReading(
                sensor_id=sensor.id,
                value=value,
                recorded_at=SCORE_END - timedelta(minutes=len(values) - index + 1),
            )
        )
    db.flush()


def _query(client, machine: Machine, **params):
    return client.get(
        f"/api/v1/machines/{machine.id}/health-score",
        params={"end": SCORE_END.isoformat(), **params},
    )


def _assert_numeric_values_are_finite(value) -> None:
    if isinstance(value, float):
        assert isfinite(value)
    elif isinstance(value, dict):
        for nested in value.values():
            _assert_numeric_values_are_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_numeric_values_are_finite(nested)


def test_zero_sensor_machine_returns_insufficient_data(client, test_machine):
    response = _query(client, test_machine)

    assert response.status_code == 200
    payload = response.json()
    assert payload["indicator_type"] == "DETERMINISTIC_MAINTENANCE_HEALTH_INDICATOR"
    assert payload["health_score"] is None
    assert payload["health_band"] == "INSUFFICIENT_DATA"
    assert payload["confidence"] == "NONE"
    assert payload["scored_sensor_count"] == 0
    assert payload["total_sensor_count"] == 0
    assert payload["most_concerning_sensor_id"] is None


def test_no_data_sensor_is_retained_but_not_numerically_scored(
    client,
    db,
    test_machine,
):
    sensor = _add_sensor(db, test_machine, name="No Data")

    payload = _query(client, test_machine).json()

    assert payload["total_sensor_count"] == 1
    assert payload["scored_sensor_count"] == 0
    assert payload["health_score"] is None
    assert payload["sensor_scores"][0]["sensor_id"] == str(sensor.id)
    assert payload["sensor_scores"][0]["health_score"] is None
    assert payload["sensor_scores"][0]["confidence"] == "NONE"


def test_one_scored_sensor_sets_machine_score_and_low_confidence(
    client,
    db,
    test_machine,
):
    sensor = _add_sensor(db, test_machine, name="Sparse")
    _add_values(db, sensor, [50])

    payload = _query(client, test_machine).json()

    assert payload["health_score"] == 100
    assert payload["health_band"] == "HEALTHY"
    assert payload["confidence"] == "LOW"
    assert payload["lowest_sensor_score"] == 100
    assert payload["most_concerning_sensor_id"] == str(sensor.id)


def test_machine_blend_excludes_no_data_and_identifies_lowest_sensor(
    client,
    db,
    test_machine,
):
    healthy = _add_sensor(db, test_machine, name="Healthy")
    concerning = _add_sensor(db, test_machine, name="Concerning")
    _add_sensor(db, test_machine, name="No Data")
    _add_values(db, healthy, [50] * 5)
    _add_values(db, concerning, [120] * 5)

    payload = _query(client, test_machine).json()
    scores = {score["sensor_id"]: score["health_score"] for score in payload["sensor_scores"]}
    expected = round(
        0.7 * ((scores[str(healthy.id)] + scores[str(concerning.id)]) / 2)
        + 0.3 * scores[str(concerning.id)],
        1,
    )

    assert payload["health_score"] == expected
    assert payload["scored_sensor_count"] == 2
    assert payload["total_sensor_count"] == 3
    assert payload["most_concerning_sensor_id"] == str(concerning.id)
    assert payload["confidence"] == "MEDIUM"


def test_equal_low_score_tie_uses_sensor_uuid(client, db, test_machine):
    later_id = _add_sensor(db, test_machine, name="Alpha")
    earlier_id = _add_sensor(db, test_machine, name="Zulu")
    earlier_id.id = UUID(int=1)
    later_id.id = UUID(int=2)
    db.flush()
    _add_values(db, earlier_id, [120] * 5)
    _add_values(db, later_id, [120] * 5)

    payload = _query(client, test_machine).json()

    assert payload["most_concerning_sensor_id"] == str(UUID(int=1))


@pytest.mark.parametrize(
    ("window", "expected_start"),
    [
        ("1h", "2026-08-28T11:00:00Z"),
        ("6h", "2026-08-28T06:00:00Z"),
        ("24h", "2026-08-27T12:00:00Z"),
        ("7d", "2026-08-21T12:00:00Z"),
    ],
)
def test_supported_windows_share_exact_feature_and_score_bounds(
    client,
    db,
    test_machine,
    window,
    expected_start,
):
    sensor = _add_sensor(db, test_machine, name="Sensor")
    _add_values(db, sensor, [50])

    payload = _query(client, test_machine, window=window).json()

    assert payload["window"] == window
    assert payload["window_start"] == expected_start
    assert payload["window_end"] == "2026-08-28T12:00:00Z"


def test_default_window_and_versions_are_explicit(client, test_machine):
    payload = _query(client, test_machine).json()

    assert payload["window"] == "24h"
    assert payload["feature_version"] == "v1"
    assert payload["scoring_version"] == "v1"


def test_omitted_end_is_current_utc_and_computed_once(client, db, test_machine):
    sensor = _add_sensor(db, test_machine, name="Sensor")
    before = datetime.now(UTC)
    response = client.get(f"/api/v1/machines/{test_machine.id}/health-score")
    after = datetime.now(UTC)

    assert response.status_code == 200
    payload = response.json()
    end = datetime.fromisoformat(payload["window_end"].replace("Z", "+00:00"))
    start = datetime.fromisoformat(payload["window_start"].replace("Z", "+00:00"))
    sensor_score = payload["sensor_scores"][0]
    assert before <= end <= after
    assert end - start == timedelta(hours=24)
    assert sensor_score["sensor_id"] == str(sensor.id)


@pytest.mark.parametrize(
    ("params", "expected_fragment"),
    [
        ({"end": "2026-08-28T12:00:00"}, "timezone"),
        ({"window": "30d"}, "Input should be"),
    ],
)
def test_invalid_end_or_window_returns_422(
    client,
    test_machine,
    params,
    expected_fragment,
):
    response = client.get(
        f"/api/v1/machines/{test_machine.id}/health-score",
        params=params,
    )

    assert response.status_code == 422
    assert expected_fragment.lower() in str(response.json()).lower()


def test_unknown_machine_returns_404(client):
    response = client.get(f"/api/v1/machines/{UUID(int=0)}/health-score")

    assert response.status_code == 404
    assert response.json() == {"detail": "Machine not found"}


def test_missing_threshold_configuration_returns_500(client, db, test_machine):
    _add_sensor(db, test_machine, name="Sensor")
    db.delete(db.get(AlertThreshold, SensorType.TEMPERATURE))
    db.flush()

    response = _query(client, test_machine)

    assert response.status_code == 500
    assert response.json() == {"detail": "Missing persisted alert thresholds for: TEMPERATURE"}


def test_explicit_historical_request_is_deterministic_and_finite(
    client,
    db,
    test_machine,
):
    sensor = _add_sensor(db, test_machine, name="Sensor")
    _add_values(db, sensor, [50, 70, 90, 91, 95])

    first = _query(client, test_machine, window="1h")
    second = _query(client, test_machine, window="1h")

    assert first.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    _assert_numeric_values_are_finite(payload)
    forbidden_fields = {
        "probability",
        "remaining_useful_life",
        "breakdown",
        "prediction",
    }
    assert forbidden_fields.isdisjoint(payload)


def test_machine_reasons_are_deterministic_and_descriptive(client, db, test_machine):
    sensor = _add_sensor(db, test_machine, name="Hot Sensor")
    _add_values(db, sensor, [100] * 5)

    reasons = _query(client, test_machine).json()["reasons"]

    assert reasons == [
        "1 of 1 sensors had readings above configured thresholds.",
        "Hot Sensor has the lowest health score.",
        "Overall data confidence is high.",
    ]
