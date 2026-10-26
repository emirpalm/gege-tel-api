from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "acme", "globex"
    name: Mapped[str]


class Line(Base):
    __tablename__ = "lines"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "L-100"
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_name: Mapped[str]
    phone_number: Mapped[str] = mapped_column(String, unique=True)
    plan: Mapped[str]  # basic | premium
    status: Mapped[str] = mapped_column(default="pending")  # pending | active | suspended
    # Timestamp (UTC, naive) del último evento de red aplicado. Sirve para descartar eventos viejos.
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class Benefit(Base):
    __tablename__ = "benefits"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "B1"
    category: Mapped[str]
    merchant: Mapped[str]
    description: Mapped[str]
    promo_code: Mapped[str]
    plans: Mapped[str]  # "basic,premium"
    valid_until: Mapped[date | None] = mapped_column(Date, default=None)  # None = sin vencimiento

    def applies_to(self, plan: str) -> bool:
        return plan in self.plans.split(",")

    def is_valid_on(self, day: date) -> bool:
        return self.valid_until is None or day <= self.valid_until


class NetworkEvent(Base):
    """Bitácora de eventos de red. La PK sobre event_id es lo que da la idempotencia."""

    __tablename__ = "network_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    line_id: Mapped[str] = mapped_column(ForeignKey("lines.id"), index=True)
    type: Mapped[str]
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    received_at: Mapped[datetime] = mapped_column(DateTime)
    outcome: Mapped[str]  # applied | ignored_stale


class Redemption(Base):
    __tablename__ = "redemptions"
    # La regla "un canje por beneficio por mes" vive en la base de datos, no solo en el código.
    __table_args__ = (UniqueConstraint("line_id", "benefit_id", "period", name="uq_redemption_per_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[str] = mapped_column(ForeignKey("lines.id"), index=True)
    benefit_id: Mapped[str] = mapped_column(ForeignKey("benefits.id"))
    period: Mapped[str]  # "2026-10" (mes en hora de Ciudad de México)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime)
