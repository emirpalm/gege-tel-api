from datetime import datetime

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import to_utc_naive
from app.models import Line, NetworkEvent

# La red es la fuente de verdad: el evento más reciente define el estado.
STATUS_BY_EVENT = {
    "activated": "active",
    "suspended": "suspended",
    "reactivated": "active",
}


class UnknownLine(Exception):
    pass


def apply_network_event(db: Session, event_id: str, line_id: str, type_: str, timestamp: datetime, now: datetime) -> str:
    """Devuelve 'applied', 'ignored_stale' o 'duplicate'."""
    if db.get(Line, line_id) is None:
        # No se registra el evento: si la red reintenta cuando la línea exista, se aplicará.
        raise UnknownLine(line_id)

    if db.get(NetworkEvent, event_id) is not None:
        return "duplicate"

    occurred_at = to_utc_naive(timestamp)
    event = NetworkEvent(
        event_id=event_id, line_id=line_id, type=type_,
        occurred_at=occurred_at, received_at=to_utc_naive(now), outcome="applied",
    )
    db.add(event)
    try:
        db.flush()  # la PK de event_id atrapa duplicados que lleguen en paralelo
    except IntegrityError:
        db.rollback()
        return "duplicate"

    # UPDATE condicional y atómico: solo cambia el estado si este evento es más nuevo que el último aplicado.
    result = db.execute(
        update(Line)
        .where(Line.id == line_id, or_(Line.last_event_at.is_(None), Line.last_event_at < occurred_at))
        .values(status=STATUS_BY_EVENT[type_], last_event_at=occurred_at)
    )
    if result.rowcount == 0:
        event.outcome = "ignored_stale"

    db.commit()
    return event.outcome
