from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import business_period, business_today, to_utc_naive
from app.models import Benefit, Line, Redemption


class LineNotActive(Exception):
    pass


class BenefitNotAvailable(Exception):
    pass


class AlreadyRedeemed(Exception):
    pass


def all_benefits(db: Session) -> list[Benefit]:
    return list(db.scalars(select(Benefit).order_by(Benefit.id)))


def eligible_benefits(db: Session, line: Line, now: datetime) -> list[Benefit]:
    """Única fuente de verdad de 'qué le aplica a esta línea hoy'. La usan el listado, el canje y el agente."""
    today = business_today(now)
    return [b for b in all_benefits(db) if b.applies_to(line.plan) and b.is_valid_on(today)]


def redeem(db: Session, line: Line, benefit_id: str, now: datetime) -> tuple[Redemption, Benefit]:
    if line.status != "active":
        raise LineNotActive(line.status)

    benefit = next((b for b in eligible_benefits(db, line, now) if b.id == benefit_id), None)
    if benefit is None:
        # Mismo error si no existe, no aplica al plan o está vencido: no damos pistas del catálogo ajeno.
        raise BenefitNotAvailable(benefit_id)

    redemption = Redemption(
        line_id=line.id, benefit_id=benefit.id,
        period=business_period(now), redeemed_at=to_utc_naive(now),
    )
    db.add(redemption)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AlreadyRedeemed(benefit_id)
    return redemption, benefit
