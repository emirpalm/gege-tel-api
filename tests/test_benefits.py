from datetime import datetime, timezone

from tests.conftest import create_line, send_event, user


def ids(resp):
    return [b["id"] for b in resp.json()]


def test_basic_plan_sees_only_its_current_benefits(client):
    line = create_line(client, plan="basic")
    resp = client.get("/me/benefits", headers=user("acme", line))
    assert ids(resp) == ["B1", "B4", "B5"]  # sin B2/B6 (premium) ni B3 (vencido)
    assert all("promo_code" not in b and "code" not in b for b in resp.json())


def test_premium_plan_sees_only_its_current_benefits(client):
    line = create_line(client, company="globex", plan="premium")
    assert ids(client.get("/me/benefits", headers=user("globex", line))) == ["B1", "B2", "B4", "B6"]


def test_expired_benefit_was_visible_before_expiration(client, clock):
    line = create_line(client, plan="basic")
    clock.now = datetime(2026, 9, 30, 23, 0, tzinfo=timezone.utc)  # 30/09 17:00 CDMX
    assert "B3" in ids(client.get("/me/benefits", headers=user("acme", line)))


def test_redeem_returns_code(client):
    line = create_line(client, plan="basic")
    resp = client.post("/me/benefits/B1/redeem", headers=user("acme", line))
    assert resp.status_code == 201
    assert resp.json()["code"] == "PARR20"
    assert resp.json()["period"] == "2026-10"


def test_cannot_redeem_same_benefit_twice_in_a_month(client, clock):
    line = create_line(client, plan="basic")
    assert client.post("/me/benefits/B1/redeem", headers=user("acme", line)).status_code == 201

    second = client.post("/me/benefits/B1/redeem", headers=user("acme", line))
    assert second.status_code == 409

    # Otro beneficio en el mismo mes sí se puede.
    assert client.post("/me/benefits/B4/redeem", headers=user("acme", line)).status_code == 201

    # El mismo beneficio el mes siguiente sí se puede.
    clock.now = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
    assert client.post("/me/benefits/B1/redeem", headers=user("acme", line)).status_code == 201


def test_month_boundary_uses_mexico_time(client, clock):
    line = create_line(client, plan="basic")
    # 31/10 21:00 CDMX = 01/11 03:00 UTC. Para el usuario sigue siendo octubre.
    clock.now = datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)
    assert client.post("/me/benefits/B1/redeem", headers=user("acme", line)).json()["period"] == "2026-10"


def test_cannot_redeem_with_suspended_line(client):
    line = create_line(client, plan="basic")
    send_event(client, line, "suspended", "2026-10-05T10:00:00Z")
    resp = client.post("/me/benefits/B1/redeem", headers=user("acme", line))
    assert resp.status_code == 409
    assert "suspended" in resp.json()["detail"]


def test_cannot_redeem_before_activation(client):
    line = create_line(client, plan="basic", active=False)
    assert client.post("/me/benefits/B1/redeem", headers=user("acme", line)).status_code == 409


def test_cannot_redeem_benefit_outside_plan_or_expired_or_unknown(client):
    line = create_line(client, plan="basic")
    for benefit_id in ["B2", "B6", "B3", "B99"]:
        assert client.post(f"/me/benefits/{benefit_id}/redeem", headers=user("acme", line)).status_code == 404
