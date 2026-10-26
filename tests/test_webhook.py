from tests.conftest import admin, create_line, send_event


def status_of(client, line_id, company="acme"):
    return client.get(f"/admin/lines/{line_id}", headers=admin(company)).json()["status"]


def test_activation_event_applies(client):
    line = create_line(client, active=False)
    resp = send_event(client, line, "activated", "2026-10-01T10:00:00Z", event_id="e-001")
    assert resp.status_code == 200
    assert resp.json() == {"event_id": "e-001", "result": "applied", "line_status": "active"}


def test_duplicate_event_leaves_state_unchanged(client):
    line = create_line(client, active=False)
    send_event(client, line, "activated", "2026-10-01T10:00:00Z", event_id="e-001")
    send_event(client, line, "suspended", "2026-10-02T10:00:00Z", event_id="e-002")

    # Reenvío de e-001: no debe reactivar la línea.
    resp = send_event(client, line, "activated", "2026-10-01T10:00:00Z", event_id="e-001")
    assert resp.status_code == 200
    assert resp.json()["result"] == "duplicate"
    assert status_of(client, line) == "suspended"

    # Reenvío del último evento: tampoco cambia nada.
    assert send_event(client, line, "suspended", "2026-10-02T10:00:00Z", event_id="e-002").json()["result"] == "duplicate"
    assert status_of(client, line) == "suspended"


def test_out_of_order_event_does_not_change_state(client):
    line = create_line(client, active=False)
    send_event(client, line, "activated", "2026-10-01T10:00:00Z", event_id="e-001")
    send_event(client, line, "suspended", "2026-10-03T10:00:00Z", event_id="e-003")

    # e-002 llega tarde con fecha anterior al último aplicado.
    resp = send_event(client, line, "reactivated", "2026-10-02T10:00:00Z", event_id="e-002")
    assert resp.json()["result"] == "ignored_stale"
    assert status_of(client, line) == "suspended"

    # Un evento posterior sí aplica.
    assert send_event(client, line, "reactivated", "2026-10-04T10:00:00Z").json()["result"] == "applied"
    assert status_of(client, line) == "active"


def test_event_order_uses_real_instant_not_text(client):
    """05:00-06:00 es 11:00Z: es POSTERIOR a 10:00Z aunque como texto parezca anterior."""
    line = create_line(client, active=False)
    send_event(client, line, "activated", "2026-10-01T10:00:00Z")
    resp = send_event(client, line, "suspended", "2026-10-01T05:00:00-06:00")
    assert resp.json()["result"] == "applied"
    assert status_of(client, line) == "suspended"


def test_event_with_same_timestamp_as_last_applied_is_ignored(client):
    line = create_line(client, active=False)
    send_event(client, line, "activated", "2026-10-01T10:00:00Z")
    assert send_event(client, line, "suspended", "2026-10-01T10:00:00Z").json()["result"] == "ignored_stale"


def test_unknown_line_returns_404(client):
    assert send_event(client, "L-999", "activated", "2026-10-01T10:00:00Z").status_code == 404


def test_invalid_payload_is_rejected(client):
    line = create_line(client, active=False)
    assert send_event(client, line, "cancelled", "2026-10-01T10:00:00Z").status_code == 422
    # Timestamp sin zona horaria: ambiguo, se rechaza.
    assert send_event(client, line, "activated", "2026-10-01T10:00:00").status_code == 422
