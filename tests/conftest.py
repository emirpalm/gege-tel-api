from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, make_engine
from app.deps import get_db, get_now, get_selector
from app.main import app
from app.seed import seed
from app.services.agent import KeywordSelector


class Clock:
    def __init__(self):
        # Lunes 26/10/2026, 12:00 en CDMX. B3 (Café Luna) ya venció.
        self.now = datetime(2026, 10, 26, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def selector_box():
    """Permite a una prueba cambiar el selector del agente (p. ej. un LLM falso que alucina)."""
    return {"selector": KeywordSelector()}


@pytest.fixture
def client(clock, selector_box):
    engine = make_engine("sqlite://", poolclass=StaticPool)  # BD en memoria, aislada por prueba
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    with TestSession() as db:
        seed(db)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_now] = lambda: clock.now
    app.dependency_overrides[get_selector] = lambda: selector_box["selector"]
    yield TestClient(app)
    app.dependency_overrides.clear()


def admin(company: str) -> dict:
    return {"X-Company-Id": company}


def user(company: str, line_id: str) -> dict:
    return {"X-Company-Id": company, "X-Line-Id": line_id}


_event_seq = iter(range(1, 10_000))


def send_event(client, line_id: str, type_: str, timestamp: str, event_id: str | None = None):
    payload = {
        "event_id": event_id or f"e-auto-{next(_event_seq)}",
        "line_id": line_id,
        "type": type_,
        "timestamp": timestamp,
    }
    return client.post("/webhooks/network", json=payload)


def create_line(client, company: str = "acme", plan: str = "basic", phone: str = "5511112222", active: bool = True) -> str:
    resp = client.post("/admin/lines", headers=admin(company), json={"employee_name": "Colaborador", "phone_number": phone, "plan": plan})
    assert resp.status_code == 201, resp.text
    line_id = resp.json()["id"]
    if active:
        assert send_event(client, line_id, "activated", "2026-10-01T10:00:00Z").json()["result"] == "applied"
    return line_id
