from uuid import uuid4

from app.models import Alert, AlertSeverity, AlertStatus


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
