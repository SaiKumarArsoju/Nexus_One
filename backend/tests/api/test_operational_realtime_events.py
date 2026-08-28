import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from app.core.enums import SensorType
from app.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertThreshold,
    Sensor,
    SensorReading,
)
from app.realtime import RealtimeEvent, event_broadcaster
from sqlalchemy import func, select


@pytest.fixture
def event_sensor(db, test_machine) -> Sensor:
    sensor = Sensor(
        name="Operational Event Temperature Sensor",
        sensor_type=SensorType.TEMPERATURE,
        unit="°C",
        machine_id=test_machine.id,
    )
    db.add(sensor)
    db.flush()

    return sensor


@contextmanager
def _captured_events() -> Iterator[asyncio.Queue[RealtimeEvent]]:
    initial_subscriber_count = event_broadcaster.subscriber_count
    queue = event_broadcaster.subscribe()

    try:
        yield queue
    finally:
        event_broadcaster.unsubscribe(queue)
        assert event_broadcaster.subscriber_count == initial_subscriber_count


def _drain(queue: asyncio.Queue[RealtimeEvent]) -> list[RealtimeEvent]:
    events = []

    while not queue.empty():
        events.append(queue.get_nowait())

    return events


def _ingest(client, sensor: Sensor, value: float):
    return client.post(
        "/api/v1/telemetry/readings",
        json={
            "sensor_id": str(sensor.id),
            "value": value,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
    )


def _temperature_alert(db, sensor: Sensor) -> Alert:
    alert = db.scalar(
        select(Alert).where(
            Alert.machine_id == sensor.machine_id,
            Alert.alert_type == "HIGH_TEMPERATURE",
        )
    )

    assert alert is not None

    return alert


def _assert_telemetry_event(
    event: RealtimeEvent,
    sensor: Sensor,
) -> None:
    assert event.type == "telemetry.updated"
    assert event.resource_id == str(sensor.id)
    assert event.data == {
        "sensor_id": str(sensor.id),
        "machine_id": str(sensor.machine_id),
    }


def _assert_alert_event(
    event: RealtimeEvent,
    alert: Alert,
    *,
    event_type: str,
    status: AlertStatus,
) -> None:
    assert event.type == event_type
    assert event.resource_id == str(alert.id)
    assert event.data == {
        "alert_id": str(alert.id),
        "machine_id": str(alert.machine_id),
        "status": status.value,
    }


def test_normal_telemetry_publishes_only_telemetry_updated(
    client,
    db,
    event_sensor,
):
    initial_reading_count = db.scalar(select(func.count()).select_from(SensorReading)) or 0

    with _captured_events() as queue:
        response = _ingest(client, event_sensor, 80.0)
        events = _drain(queue)

    assert response.status_code == 201
    assert db.scalar(select(func.count()).select_from(SensorReading)) == initial_reading_count + 1
    assert len(events) == 1
    _assert_telemetry_event(events[0], event_sensor)


def test_abnormal_telemetry_publishes_ordered_telemetry_and_alert_events(
    client,
    db,
    event_sensor,
):
    with _captured_events() as queue:
        response = _ingest(client, event_sensor, 100.0)
        events = _drain(queue)

    alert = _temperature_alert(db, event_sensor)

    assert response.status_code == 201
    assert len(events) == 2
    _assert_telemetry_event(events[0], event_sensor)
    _assert_alert_event(
        events[1],
        alert,
        event_type="alert.created",
        status=AlertStatus.ACTIVE,
    )


def test_repeated_abnormal_telemetry_with_active_alert_publishes_no_alert_event(
    client,
    db,
    event_sensor,
):
    assert _ingest(client, event_sensor, 100.0).status_code == 201

    with _captured_events() as queue:
        response = _ingest(client, event_sensor, 101.0)
        events = _drain(queue)

    assert response.status_code == 201
    assert len(events) == 1
    _assert_telemetry_event(events[0], event_sensor)
    assert _temperature_alert(db, event_sensor).status == AlertStatus.ACTIVE


def test_repeated_abnormal_telemetry_with_acknowledged_alert_publishes_no_alert_event(
    client,
    db,
    event_sensor,
):
    assert _ingest(client, event_sensor, 100.0).status_code == 201
    alert = _temperature_alert(db, event_sensor)
    alert.status = AlertStatus.ACKNOWLEDGED
    db.flush()

    with _captured_events() as queue:
        response = _ingest(client, event_sensor, 101.0)
        events = _drain(queue)

    db.refresh(alert)
    assert response.status_code == 201
    assert len(events) == 1
    _assert_telemetry_event(events[0], event_sensor)
    assert alert.status == AlertStatus.ACKNOWLEDGED


@pytest.mark.parametrize(
    "initial_status",
    [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED],
)
def test_normal_telemetry_publishes_resolution_for_open_alert(
    client,
    db,
    event_sensor,
    initial_status,
):
    assert _ingest(client, event_sensor, 100.0).status_code == 201
    alert = _temperature_alert(db, event_sensor)
    alert.status = initial_status
    db.flush()

    with _captured_events() as queue:
        response = _ingest(client, event_sensor, 80.0)
        events = _drain(queue)

    db.refresh(alert)
    assert response.status_code == 201
    assert len(events) == 2
    _assert_telemetry_event(events[0], event_sensor)
    _assert_alert_event(
        events[1],
        alert,
        event_type="alert.updated",
        status=AlertStatus.RESOLVED,
    )


def test_missing_threshold_rolls_back_without_publishing(
    client,
    db,
    event_sensor,
):
    threshold = db.get(AlertThreshold, SensorType.TEMPERATURE)
    assert threshold is not None
    db.delete(threshold)
    db.flush()

    initial_reading_count = db.scalar(select(func.count()).select_from(SensorReading)) or 0
    initial_alert_count = db.scalar(select(func.count()).select_from(Alert)) or 0

    with _captured_events() as queue:
        response = _ingest(client, event_sensor, 100.0)
        events = _drain(queue)

    assert response.status_code == 500
    assert events == []
    assert db.scalar(select(func.count()).select_from(SensorReading)) == initial_reading_count
    assert db.scalar(select(func.count()).select_from(Alert)) == initial_alert_count


def test_manual_alert_lifecycle_publishes_only_real_transitions(
    client,
    db,
    test_machine,
):
    alert = Alert(
        machine_id=test_machine.id,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.ACTIVE,
        alert_type="MANUAL_EVENT_TEST",
        message="Manual event test",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    with _captured_events() as queue:
        response = client.patch(f"/api/v1/alerts/{alert.id}/acknowledge")
        events = _drain(queue)

    assert response.status_code == 200
    assert len(events) == 1
    _assert_alert_event(
        events[0],
        alert,
        event_type="alert.updated",
        status=AlertStatus.ACKNOWLEDGED,
    )

    with _captured_events() as queue:
        response = client.patch(f"/api/v1/alerts/{alert.id}/acknowledge")
        events = _drain(queue)

    assert response.status_code == 200
    assert events == []

    with _captured_events() as queue:
        response = client.patch(f"/api/v1/alerts/{alert.id}/resolve")
        events = _drain(queue)

    assert response.status_code == 200
    assert len(events) == 1
    _assert_alert_event(
        events[0],
        alert,
        event_type="alert.updated",
        status=AlertStatus.RESOLVED,
    )

    with _captured_events() as queue:
        response = client.patch(f"/api/v1/alerts/{alert.id}/resolve")
        events = _drain(queue)

    assert response.status_code == 200
    assert events == []


def test_alert_sync_publishes_created_and_resolved_changes(
    client,
    db,
    event_sensor,
):
    recorded_at = datetime(2030, 1, 1, tzinfo=UTC)
    db.add(
        SensorReading(
            sensor_id=event_sensor.id,
            value=100.0,
            recorded_at=recorded_at,
        )
    )
    db.flush()

    with _captured_events() as queue:
        response = client.post("/api/v1/alerts/sync")
        events = _drain(queue)

    alert = _temperature_alert(db, event_sensor)

    assert response.status_code == 200
    assert response.json() == {"created_alerts": 1}
    assert len(events) == 1
    _assert_alert_event(
        events[0],
        alert,
        event_type="alert.created",
        status=AlertStatus.ACTIVE,
    )

    db.add(
        SensorReading(
            sensor_id=event_sensor.id,
            value=80.0,
            recorded_at=recorded_at + timedelta(minutes=1),
        )
    )
    db.flush()

    with _captured_events() as queue:
        response = client.post("/api/v1/alerts/sync")
        events = _drain(queue)

    db.refresh(alert)
    assert response.status_code == 200
    assert response.json() == {"created_alerts": 0}
    assert len(events) == 1
    _assert_alert_event(
        events[0],
        alert,
        event_type="alert.updated",
        status=AlertStatus.RESOLVED,
    )


def test_failed_ingestion_commit_publishes_no_event(
    client,
    db,
    event_sensor,
    monkeypatch,
):
    def fail_commit() -> None:
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(db, "commit", fail_commit)

    with _captured_events() as queue:
        with pytest.raises(RuntimeError, match="forced commit failure"):
            _ingest(client, event_sensor, 80.0)

        events = _drain(queue)

    assert events == []

    for reading in db.scalars(
        select(SensorReading).where(SensorReading.sensor_id == event_sensor.id)
    ):
        db.delete(reading)

    db.flush()


def test_broadcaster_failure_does_not_report_committed_ingestion_as_failed(
    client,
    db,
    event_sensor,
    monkeypatch,
):
    async def fail_publish(event: RealtimeEvent) -> None:
        raise RuntimeError(f"forced publish failure for {event.type}")

    monkeypatch.setattr(event_broadcaster, "publish", fail_publish)

    response = _ingest(client, event_sensor, 80.0)

    assert response.status_code == 201
    assert db.get(SensorReading, response.json()["id"]) is not None
