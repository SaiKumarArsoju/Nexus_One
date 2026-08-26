from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models import Alert, AlertSeverity, AlertStatus


def _create_alert(
    db,
    test_machine,
    *,
    status: AlertStatus,
    alert_type: str,
    created_at: datetime | None = None,
) -> Alert:
    alert = Alert(
        machine_id=test_machine.id,
        severity=AlertSeverity.WARNING,
        status=status,
        alert_type=alert_type,
        message=f"{alert_type} message",
    )

    if created_at is not None:
        alert.created_at = created_at

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert


def test_get_alert_history_returns_success(client):
    response = client.get("/api/v1/alerts/history")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_resolved_alert_appears_only_in_history(client, db, test_machine):
    alert = _create_alert(
        db,
        test_machine,
        status=AlertStatus.RESOLVED,
        alert_type="TEST_RESOLVED_HISTORY",
    )

    history_response = client.get("/api/v1/alerts/history")
    active_response = client.get("/api/v1/alerts")

    assert history_response.status_code == 200
    assert active_response.status_code == 200
    assert str(alert.id) in {item["id"] for item in history_response.json()}
    assert str(alert.id) not in {item["id"] for item in active_response.json()}


def test_active_alert_appears_in_history(client, db, test_machine):
    alert = _create_alert(
        db,
        test_machine,
        status=AlertStatus.ACTIVE,
        alert_type="TEST_ACTIVE_HISTORY",
    )

    response = client.get("/api/v1/alerts/history")

    assert response.status_code == 200
    assert str(alert.id) in {item["id"] for item in response.json()}


def test_acknowledged_alert_appears_in_history(client, db, test_machine):
    alert = _create_alert(
        db,
        test_machine,
        status=AlertStatus.ACKNOWLEDGED,
        alert_type="TEST_ACKNOWLEDGED_HISTORY",
    )

    response = client.get("/api/v1/alerts/history")

    assert response.status_code == 200
    assert str(alert.id) in {item["id"] for item in response.json()}


def test_alert_history_is_newest_first(client, db, test_machine):
    older_time = datetime(2026, 1, 1, tzinfo=UTC)
    newer_time = older_time + timedelta(days=1)
    older_alert = _create_alert(
        db,
        test_machine,
        status=AlertStatus.RESOLVED,
        alert_type="TEST_OLDER_HISTORY",
        created_at=older_time,
    )
    newer_alert = _create_alert(
        db,
        test_machine,
        status=AlertStatus.ACTIVE,
        alert_type="TEST_NEWER_HISTORY",
        created_at=newer_time,
    )

    response = client.get("/api/v1/alerts/history")
    response_ids = [item["id"] for item in response.json()]

    assert response.status_code == 200
    assert response_ids.index(str(newer_alert.id)) < response_ids.index(str(older_alert.id))


def test_get_alerts_returns_success(client):
    response = client.get("/api/v1/alerts")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_acknowledge_alert(client, db, test_machine):
    alert = Alert(
        machine_id=test_machine.id,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.ACTIVE,
        alert_type="TEST_ALERT",
        message="Test alert",
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    response = client.patch(f"/api/v1/alerts/{alert.id}/acknowledge")

    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"


def test_resolve_acknowledged_alert(client, db, test_machine):
    alert = Alert(
        machine_id=test_machine.id,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACKNOWLEDGED,
        alert_type="TEST_ALERT",
        message="Test alert",
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    response = client.patch(f"/api/v1/alerts/{alert.id}/resolve")

    assert response.status_code == 200
    assert response.json()["status"] == "RESOLVED"


def test_acknowledge_missing_alert_returns_404(client):
    response = client.patch(f"/api/v1/alerts/{uuid4()}/acknowledge")

    assert response.status_code == 404


def test_resolved_alert_cannot_be_acknowledged(
    client,
    db,
    test_machine,
):
    alert = Alert(
        machine_id=test_machine.id,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.RESOLVED,
        alert_type="TEST_ALERT",
        message="Test alert",
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    response = client.patch(f"/api/v1/alerts/{alert.id}/acknowledge")

    assert response.status_code == 409
