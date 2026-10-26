from tests.conftest import admin, create_line, user


def test_admin_creates_line_as_pending(client):
    resp = client.post("/admin/lines", headers=admin("acme"), json={"employee_name": "Ana", "phone_number": "5512345678", "plan": "premium"})
    assert resp.status_code == 201
    assert resp.json()["company_id"] == "acme"
    assert resp.json()["status"] == "pending"


def test_company_cannot_see_or_modify_other_company_lines(client):
    acme_line = create_line(client, company="acme")

    # Globex no la ve en su listado...
    assert client.get("/admin/lines", headers=admin("globex")).json() == []
    # ...ni por ID, ni puede modificarla (404, no 403: no revela que existe).
    assert client.get(f"/admin/lines/{acme_line}", headers=admin("globex")).status_code == 404
    assert client.patch(f"/admin/lines/{acme_line}", headers=admin("globex"), json={"plan": "premium"}).status_code == 404
    # ...ni puede usarla como colaborador.
    assert client.get("/me/benefits", headers=user("globex", acme_line)).status_code == 404
    assert client.post("/me/benefits/B1/redeem", headers=user("globex", acme_line)).status_code == 404
    assert client.post("/me/agent", headers=user("globex", acme_line), json={"question": "¿qué tengo?"}).status_code == 404

    # La línea sigue intacta para Acme.
    line = client.get(f"/admin/lines/{acme_line}", headers=admin("acme")).json()
    assert line["plan"] == "basic"


def test_missing_or_unknown_company_header_is_rejected(client):
    assert client.get("/admin/lines").status_code == 401
    assert client.get("/admin/lines", headers=admin("initech")).status_code == 401


def test_duplicate_phone_number_is_rejected(client):
    create_line(client, company="acme", phone="5500000001", active=False)
    resp = client.post("/admin/lines", headers=admin("globex"), json={"employee_name": "X", "phone_number": "5500000001", "plan": "basic"})
    assert resp.status_code == 409
