import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.deps import current_company, current_line, get_company_line, get_db, get_now, get_selector
from app.models import Company, Line
from app.schemas import (
    AgentAnswer, AgentQuestion, BenefitOut, LineCreate, LineOut, LineUpdate,
    NetworkEventIn, NetworkEventOut, RedemptionOut,
)
from app.seed import seed
from app.services import agent, benefits, network


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db, demo_lines=os.getenv("DEMO_SEED") == "true")
    yield


app = FastAPI(title="Gege Tel API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


# --- 1. Alta por empresa (administradora) -------------------------------------------------

@app.post("/admin/lines", response_model=LineOut, status_code=201)
def create_line(body: LineCreate, company: Company = Depends(current_company), db: Session = Depends(get_db)):
    line = Line(id=_next_line_id(db), company_id=company.id, **body.model_dump())
    db.add(line)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "El número ya está dado de alta")
    return line


@app.get("/admin/lines", response_model=list[LineOut])
def list_lines(company: Company = Depends(current_company), db: Session = Depends(get_db)):
    return db.scalars(select(Line).where(Line.company_id == company.id).order_by(Line.id)).all()


@app.get("/admin/lines/{line_id}", response_model=LineOut)
def get_line(line_id: str, company: Company = Depends(current_company), db: Session = Depends(get_db)):
    return get_company_line(db, company, line_id)


@app.patch("/admin/lines/{line_id}", response_model=LineOut)
def update_line(line_id: str, body: LineUpdate, company: Company = Depends(current_company), db: Session = Depends(get_db)):
    line = get_company_line(db, company, line_id)
    line.plan = body.plan
    db.commit()
    return line


def _next_line_id(db: Session) -> str:
    # Suficiente para la prueba (SQLite serializa escrituras); en producción el ID lo asignaría la red.
    numbers = [int(i.split("-")[1]) for i in db.scalars(select(Line.id))]
    return f"L-{max(numbers, default=99) + 1}"


# --- 2. Webhook de la red -----------------------------------------------------------------

@app.post("/webhooks/network", response_model=NetworkEventOut)
def network_webhook(event: NetworkEventIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    try:
        result = network.apply_network_event(db, event.event_id, event.line_id, event.type, event.timestamp, now)
    except network.UnknownLine:
        raise HTTPException(404, "Línea desconocida")
    line = db.get(Line, event.line_id)
    db.refresh(line)
    return NetworkEventOut(event_id=event.event_id, result=result, line_status=line.status)


# --- 3. Beneficios y canje (colaborador) --------------------------------------------------

@app.get("/me/benefits", response_model=list[BenefitOut])
def my_benefits(line: Line = Depends(current_line), db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    return benefits.eligible_benefits(db, line, now)


@app.post("/me/benefits/{benefit_id}/redeem", response_model=RedemptionOut, status_code=201)
def redeem_benefit(benefit_id: str, line: Line = Depends(current_line), db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    try:
        redemption, benefit = benefits.redeem(db, line, benefit_id, now)
    except benefits.LineNotActive as exc:
        raise HTTPException(409, f"La línea no está activa (estado: {exc.args[0]})")
    except benefits.BenefitNotAvailable:
        raise HTTPException(404, "Beneficio no disponible para tu plan")
    except benefits.AlreadyRedeemed:
        raise HTTPException(409, "Ya canjeaste este beneficio este mes")
    return RedemptionOut(
        benefit_id=benefit.id, merchant=benefit.merchant, code=benefit.promo_code,
        period=redemption.period, redeemed_at=redemption.redeemed_at.replace(tzinfo=timezone.utc),
    )


# --- 4. Agente ----------------------------------------------------------------------------

@app.post("/me/agent", response_model=AgentAnswer)
def ask_agent(
    body: AgentQuestion,
    line: Line = Depends(current_line),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
    selector: agent.BenefitSelector = Depends(get_selector),
):
    candidates = benefits.eligible_benefits(db, line, now)
    text, chosen = agent.answer(body.question, line.plan, candidates, benefits.all_benefits(db), selector)
    return AgentAnswer(answer=text, benefits=chosen, selector=selector.name)
