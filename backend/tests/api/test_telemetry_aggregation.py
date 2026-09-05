from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.enums import SensorType
from app.models import Sensor, SensorReading


@pytest.fixture
def aggregation_sensor(db, test_machine) -> Sensor:
    sensor = Sensor(
        name="Telemetry Aggregation Temperature Sensor",
        sensor_type=SensorType.TEMPERATURE,
        unit="°C",
        machine_id=test_machine.id,
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
) -> None:
    db.add(
        SensorReading(
            sensor_id=sensor.id,
            value=value,
            recorded_at=recorded_at,
        )
    )


def _query_aggregate(
    client,
    sensor: Sensor,
    *,
    start: str = "2026-08-28T12:00:00Z",
    end: str = "2026-08-28T14:00:00Z",
    bucket: str = "5m",
):
    return client.get(
        "/api/v1/telemetry/aggregate",
        params={
            "sensor_id": str(sensor.id),
            "start": start,
            "end": end,
            "bucket": bucket,
        },
    )


def test_existing_sensor_returns_ordered_aggregate_buckets_with_correct_math(
    client,
    db,
    aggregation_sensor,
):
    readings = [
        (datetime(2026, 8, 28, 12, 6, tzinfo=UTC), 30.0),
        (datetime(2026, 8, 28, 12, 1, tzinfo=UTC), 10.0),
        (datetime(2026, 8, 28, 12, 4, tzinfo=UTC), 20.0),
    ]
    for recorded_at, value in readings:
        _add_reading(
            db,
            aggregation_sensor,
            value=value,
            recorded_at=recorded_at,
        )
    db.flush()

    response = _query_aggregate(client, aggregation_sensor)

    assert response.status_code == 200
    assert response.json() == [
        {
            "bucket_start": "2026-08-28T12:00:00Z",
            "average": 15.0,
            "minimum": 10.0,
            "maximum": 20.0,
            "count": 2,
        },
        {
            "bucket_start": "2026-08-28T12:05:00Z",
            "average": 30.0,
            "minimum": 30.0,
            "maximum": 30.0,
            "count": 1,
        },
    ]


def test_unknown_sensor_returns_404(client):
    response = client.get(
        "/api/v1/telemetry/aggregate",
        params={
            "sensor_id": str(uuid4()),
            "start": "2026-08-28T12:00:00Z",
            "end": "2026-08-28T13:00:00Z",
            "bucket": "5m",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Sensor not found"}


def test_existing_sensor_without_matching_readings_returns_empty_list(
    client,
    aggregation_sensor,
):
    response = _query_aggregate(client, aggregation_sensor)

    assert response.status_code == 200
    assert response.json() == []


def test_start_boundary_is_inclusive(client, db, aggregation_sensor):
    start = datetime(2026, 8, 28, 12, tzinfo=UTC)
    _add_reading(
        db,
        aggregation_sensor,
        value=42.0,
        recorded_at=start,
    )
    db.flush()

    response = _query_aggregate(client, aggregation_sensor)

    assert response.status_code == 200
    assert response.json()[0]["count"] == 1
    assert response.json()[0]["average"] == 42.0


def test_end_boundary_is_exclusive(client, db, aggregation_sensor):
    end = datetime(2026, 8, 28, 14, tzinfo=UTC)
    _add_reading(
        db,
        aggregation_sensor,
        value=42.0,
        recorded_at=end,
    )
    db.flush()

    response = _query_aggregate(client, aggregation_sensor)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(
            "2026-08-28T12:00:00Z",
            "2026-08-28T12:00:00Z",
            id="equal",
        ),
        pytest.param(
            "2026-08-28T13:00:00Z",
            "2026-08-28T12:00:00Z",
            id="start-after-end",
        ),
    ],
)
def test_invalid_range_returns_422(client, aggregation_sensor, start, end):
    response = _query_aggregate(
        client,
        aggregation_sensor,
        start=start,
        end=end,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "start must be earlier than end"}


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(
            "2026-08-28T12:00:00",
            "2026-08-28T13:00:00Z",
            id="naive-start",
        ),
        pytest.param(
            "2026-08-28T12:00:00Z",
            "2026-08-28T13:00:00",
            id="naive-end",
        ),
    ],
)
def test_naive_datetime_returns_422(client, aggregation_sensor, start, end):
    response = _query_aggregate(
        client,
        aggregation_sensor,
        start=start,
        end=end,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "bucket",
    [
        pytest.param("2m", id="two-minutes"),
        pytest.param("30m", id="thirty-minutes"),
        pytest.param("day", id="word"),
        pytest.param("1d", id="one-day"),
        pytest.param("DROP TABLE sensor_readings", id="sql-text"),
        pytest.param("", id="empty"),
    ],
)
def test_unsupported_bucket_returns_422(client, aggregation_sensor, bucket):
    response = _query_aggregate(
        client,
        aggregation_sensor,
        bucket=bucket,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("bucket", "expected_bucket_start"),
    [
        pytest.param("1m", "2026-08-28T12:16:00Z", id="one-minute"),
        pytest.param("5m", "2026-08-28T12:15:00Z", id="five-minutes"),
        pytest.param("15m", "2026-08-28T12:15:00Z", id="fifteen-minutes"),
        pytest.param("1h", "2026-08-28T12:00:00Z", id="one-hour"),
    ],
)
def test_supported_bucket_aggregates_reading(
    client,
    db,
    aggregation_sensor,
    bucket,
    expected_bucket_start,
):
    _add_reading(
        db,
        aggregation_sensor,
        value=75.0,
        recorded_at=datetime(2026, 8, 28, 12, 16, 30, tzinfo=UTC),
    )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        bucket=bucket,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "bucket_start": expected_bucket_start,
            "average": 75.0,
            "minimum": 75.0,
            "maximum": 75.0,
            "count": 1,
        }
    ]


def test_bucket_alignment_uses_absolute_utc_boundaries(
    client,
    db,
    aggregation_sensor,
):
    _add_reading(
        db,
        aggregation_sensor,
        value=72.0,
        recorded_at=datetime(2026, 8, 28, 12, 4, tzinfo=UTC),
    )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        start="2026-08-28T12:03:00Z",
        end="2026-08-28T12:10:00Z",
    )

    assert response.status_code == 200
    assert response.json()[0]["bucket_start"] == "2026-08-28T12:00:00Z"


def test_partial_first_bucket_excludes_readings_before_start(
    client,
    db,
    aggregation_sensor,
):
    for minute, value in [(2, 1000.0), (4, 20.0)]:
        _add_reading(
            db,
            aggregation_sensor,
            value=value,
            recorded_at=datetime(2026, 8, 28, 12, minute, tzinfo=UTC),
        )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        start="2026-08-28T12:03:00Z",
        end="2026-08-28T12:05:00Z",
    )

    assert response.status_code == 200
    assert response.json()[0]["average"] == 20.0
    assert response.json()[0]["count"] == 1


def test_partial_last_bucket_excludes_readings_at_or_after_end(
    client,
    db,
    aggregation_sensor,
):
    for minute, value in [(6, 20.0), (8, 1000.0)]:
        _add_reading(
            db,
            aggregation_sensor,
            value=value,
            recorded_at=datetime(2026, 8, 28, 12, minute, tzinfo=UTC),
        )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        start="2026-08-28T12:05:00Z",
        end="2026-08-28T12:08:00Z",
    )

    assert response.status_code == 200
    assert response.json()[0]["average"] == 20.0
    assert response.json()[0]["count"] == 1


def test_empty_intermediate_buckets_are_omitted(
    client,
    db,
    aggregation_sensor,
):
    for minute in [1, 11]:
        _add_reading(
            db,
            aggregation_sensor,
            value=float(minute),
            recorded_at=datetime(2026, 8, 28, 12, minute, tzinfo=UTC),
        )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        end="2026-08-28T12:15:00Z",
    )

    assert response.status_code == 200
    assert [bucket["bucket_start"] for bucket in response.json()] == [
        "2026-08-28T12:00:00Z",
        "2026-08-28T12:10:00Z",
    ]


@pytest.mark.parametrize(
    ("end", "expected_status"),
    [
        pytest.param("2026-09-28T12:00:00Z", 200, id="exactly-31-days"),
        pytest.param("2026-09-28T12:00:00.000001Z", 422, id="over-31-days"),
    ],
)
def test_aggregation_range_limit(
    client,
    aggregation_sensor,
    end,
    expected_status,
):
    response = _query_aggregate(
        client,
        aggregation_sensor,
        end=end,
    )

    assert response.status_code == expected_status
    if expected_status == 422:
        assert response.json() == {"detail": "aggregation range must not exceed 31 days"}


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(
            "2026-08-28T17:33:00+05:30",
            "2026-08-28T17:40:00+05:30",
            id="positive-offset",
        ),
        pytest.param(
            "2026-08-28T08:03:00-04:00",
            "2026-08-28T08:10:00-04:00",
            id="negative-offset",
        ),
    ],
)
def test_timezone_offsets_are_normalized_to_utc(
    client,
    db,
    aggregation_sensor,
    start,
    end,
):
    _add_reading(
        db,
        aggregation_sensor,
        value=72.0,
        recorded_at=datetime(2026, 8, 28, 12, 4, tzinfo=UTC),
    )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        start=start,
        end=end,
    )

    assert response.status_code == 200
    assert response.json()[0]["bucket_start"] == "2026-08-28T12:00:00Z"


def test_dst_adjacent_offsets_are_compared_as_absolute_instants(
    client,
    db,
    aggregation_sensor,
):
    for recorded_at, value in [
        (datetime(2026, 11, 1, 5, 45, tzinfo=UTC), 70.0),
        (datetime(2026, 11, 1, 6, 15, tzinfo=UTC), 80.0),
    ]:
        _add_reading(
            db,
            aggregation_sensor,
            value=value,
            recorded_at=recorded_at,
        )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        start="2026-11-01T01:30:00-04:00",
        end="2026-11-01T01:30:00-05:00",
        bucket="1h",
    )

    assert response.status_code == 200
    assert [bucket["bucket_start"] for bucket in response.json()] == [
        "2026-11-01T05:00:00Z",
        "2026-11-01T06:00:00Z",
    ]


def test_hour_buckets_align_across_utc_midnight(
    client,
    db,
    aggregation_sensor,
):
    for recorded_at in [
        datetime(2026, 8, 28, 23, 59, 59, tzinfo=UTC),
        datetime(2026, 8, 29, 0, 0, tzinfo=UTC),
    ]:
        _add_reading(
            db,
            aggregation_sensor,
            value=72.0,
            recorded_at=recorded_at,
        )
    db.flush()

    response = _query_aggregate(
        client,
        aggregation_sensor,
        start="2026-08-28T23:59:00Z",
        end="2026-08-29T00:01:00Z",
        bucket="1h",
    )

    assert response.status_code == 200
    assert [bucket["bucket_start"] for bucket in response.json()] == [
        "2026-08-28T23:00:00Z",
        "2026-08-29T00:00:00Z",
    ]


def test_multiple_readings_at_same_timestamp_aggregate_together(
    client,
    db,
    aggregation_sensor,
):
    recorded_at = datetime(2026, 8, 28, 12, 1, tzinfo=UTC)
    for value in [10.0, 20.0, 30.0]:
        _add_reading(
            db,
            aggregation_sensor,
            value=value,
            recorded_at=recorded_at,
        )
    db.flush()

    response = _query_aggregate(client, aggregation_sensor)
    bucket = response.json()[0]

    assert response.status_code == 200
    assert bucket["average"] == 20.0
    assert bucket["minimum"] == 10.0
    assert bucket["maximum"] == 30.0
    assert bucket["count"] == 3


@pytest.mark.parametrize("missing_parameter", ["start", "end"])
def test_required_time_bound_returns_422(
    client,
    aggregation_sensor,
    missing_parameter,
):
    params = {
        "sensor_id": str(aggregation_sensor.id),
        "start": "2026-08-28T12:00:00Z",
        "end": "2026-08-28T13:00:00Z",
        "bucket": "5m",
    }
    del params[missing_parameter]

    response = client.get("/api/v1/telemetry/aggregate", params=params)

    assert response.status_code == 422
