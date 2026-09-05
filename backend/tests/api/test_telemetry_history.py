from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.core.enums import SensorType
from app.models import Sensor, SensorReading


@pytest.fixture
def history_sensor(db, test_machine) -> Sensor:
    sensor = Sensor(
        name="Historical Telemetry Temperature Sensor",
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


def _query_history(client, sensor: Sensor, **params):
    return client.get(
        "/api/v1/telemetry/readings",
        params={
            "sensor_id": str(sensor.id),
            **params,
        },
    )


def _response_datetimes(response) -> list[datetime]:
    return [
        datetime.fromisoformat(reading["recorded_at"].replace("Z", "+00:00"))
        for reading in response.json()
    ]


def test_existing_sensor_returns_historical_readings(
    client,
    db,
    history_sensor,
):
    recorded_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    reading = _add_reading(
        db,
        history_sensor,
        value=82.4,
        recorded_at=recorded_at,
    )
    db.flush()

    response = _query_history(client, history_sensor)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(reading.id),
            "sensor_id": str(history_sensor.id),
            "value": 82.4,
            "recorded_at": "2026-08-28T12:00:00Z",
        }
    ]


def test_unknown_sensor_returns_404(client):
    response = client.get(
        "/api/v1/telemetry/readings",
        params={"sensor_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Sensor not found"}


def test_existing_sensor_without_readings_returns_empty_list(
    client,
    history_sensor,
):
    response = _query_history(client, history_sensor)

    assert response.status_code == 200
    assert response.json() == []


def test_results_are_ordered_oldest_to_newest(
    client,
    db,
    history_sensor,
):
    base = datetime(2026, 8, 28, 12, tzinfo=UTC)

    for offset in [2, 0, 1]:
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=base + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(client, history_sensor)

    assert response.status_code == 200
    assert _response_datetimes(response) == [
        base,
        base + timedelta(minutes=1),
        base + timedelta(minutes=2),
    ]


def test_start_filter_is_inclusive(client, db, history_sensor):
    start = datetime(2026, 8, 28, 12, tzinfo=UTC)

    for offset in [-1, 0, 1]:
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=start + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(
        client,
        history_sensor,
        start=start.isoformat(),
    )

    assert response.status_code == 200
    assert _response_datetimes(response) == [
        start,
        start + timedelta(minutes=1),
    ]


def test_end_filter_is_inclusive(client, db, history_sensor):
    end = datetime(2026, 8, 28, 12, tzinfo=UTC)

    for offset in [-1, 0, 1]:
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=end + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(
        client,
        history_sensor,
        end=end.isoformat(),
    )

    assert response.status_code == 200
    assert _response_datetimes(response) == [
        end - timedelta(minutes=1),
        end,
    ]


def test_start_and_end_filter_range(client, db, history_sensor):
    base = datetime(2026, 8, 28, 12, tzinfo=UTC)

    for offset in range(5):
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=base + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(
        client,
        history_sensor,
        start=(base + timedelta(minutes=1)).isoformat(),
        end=(base + timedelta(minutes=3)).isoformat(),
    )

    assert response.status_code == 200
    assert _response_datetimes(response) == [
        base + timedelta(minutes=1),
        base + timedelta(minutes=2),
        base + timedelta(minutes=3),
    ]


def test_equal_start_and_end_include_reading_at_exact_instant(
    client,
    db,
    history_sensor,
):
    recorded_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    _add_reading(
        db,
        history_sensor,
        value=72.5,
        recorded_at=recorded_at,
    )
    db.flush()

    response = _query_history(
        client,
        history_sensor,
        start=recorded_at.isoformat(),
        end=recorded_at.isoformat(),
    )

    assert response.status_code == 200
    assert _response_datetimes(response) == [recorded_at]


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(
            "2026-08-28T17:29:00+05:30",
            "2026-08-28T17:31:00+05:30",
            id="positive-offset",
        ),
        pytest.param(
            "2026-08-28T07:59:00-04:00",
            "2026-08-28T08:01:00-04:00",
            id="negative-offset",
        ),
    ],
)
def test_timezone_offsets_are_normalized_for_raw_history(
    client,
    db,
    history_sensor,
    start,
    end,
):
    recorded_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    _add_reading(
        db,
        history_sensor,
        value=72.5,
        recorded_at=recorded_at,
    )
    db.flush()

    response = _query_history(
        client,
        history_sensor,
        start=start,
        end=end,
    )

    assert response.status_code == 200
    assert _response_datetimes(response) == [recorded_at]


def test_start_after_end_returns_422(client, history_sensor):
    response = _query_history(
        client,
        history_sensor,
        start="2026-08-28T13:00:00Z",
        end="2026-08-28T12:00:00Z",
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "start must be less than or equal to end"}


def test_naive_start_returns_422(client, history_sensor):
    response = _query_history(
        client,
        history_sensor,
        start="2026-08-28T12:00:00",
    )

    assert response.status_code == 422


def test_naive_end_returns_422(client, history_sensor):
    response = _query_history(
        client,
        history_sensor,
        end="2026-08-28T12:00:00",
    )

    assert response.status_code == 422


def test_default_limit_selects_newest_500_readings(
    client,
    db,
    history_sensor,
):
    base = datetime(2026, 8, 1, tzinfo=UTC)

    for offset in range(501):
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=base + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(client, history_sensor)
    readings = response.json()

    assert response.status_code == 200
    assert len(readings) == 500
    assert readings[0]["value"] == 1.0
    assert readings[-1]["value"] == 500.0


def test_custom_limit_is_enforced(client, db, history_sensor):
    base = datetime(2026, 8, 28, 12, tzinfo=UTC)

    for offset in range(4):
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=base + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(client, history_sensor, limit=3)

    assert response.status_code == 200
    assert [reading["value"] for reading in response.json()] == [
        1.0,
        2.0,
        3.0,
    ]


@pytest.mark.parametrize(
    "limit",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(5001, id="above-maximum"),
    ],
)
def test_invalid_limit_returns_422(client, history_sensor, limit):
    response = _query_history(
        client,
        history_sensor,
        limit=limit,
    )

    assert response.status_code == 422


def test_limit_selects_newest_rows_then_returns_them_ascending(
    client,
    db,
    history_sensor,
):
    base = datetime(2026, 8, 28, 12, tzinfo=UTC)

    for offset in range(5):
        _add_reading(
            db,
            history_sensor,
            value=float(offset),
            recorded_at=base + timedelta(minutes=offset),
        )

    db.flush()
    response = _query_history(client, history_sensor, limit=2)

    assert response.status_code == 200
    assert [reading["value"] for reading in response.json()] == [
        3.0,
        4.0,
    ]


def test_identical_timestamps_are_ordered_by_id_ascending(
    client,
    db,
    history_sensor,
):
    recorded_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    reading_ids = [
        UUID("00000000-0000-0000-0000-000000000003"),
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000000002"),
    ]

    for reading_id in reading_ids:
        _add_reading(
            db,
            history_sensor,
            reading_id=reading_id,
            value=float(reading_id.int),
            recorded_at=recorded_at,
        )

    db.flush()
    response = _query_history(client, history_sensor)

    assert response.status_code == 200
    assert [reading["id"] for reading in response.json()] == [
        str(reading_id) for reading_id in sorted(reading_ids)
    ]
