from collections.abc import Iterator
from datetime import datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.db import SessionLocal
from app.models import Company, Line
from app.services.agent import BenefitSelector, selector_from_env


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_now() -> datetime:
    """Reloj inyectable: las pruebas lo reemplazan para controlar vigencias y meses."""
    return utc_now()


def get_selector() -> BenefitSelector:
    return selector_from_env()


def current_company(
    x_company_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Company:
    """Simula la sesión de la administradora: la empresa viene en el encabezado X-Company-Id."""
    company = db.get(Company, x_company_id) if x_company_id else None
    if company is None:
        raise HTTPException(401, "Encabezado X-Company-Id ausente o empresa desconocida")
    return company


def current_line(
    x_line_id: str | None = Header(default=None),
    company: Company = Depends(current_company),
    db: Session = Depends(get_db),
) -> Line:
    """Simula la sesión del colaborador: empresa + línea. La línea siempre se busca dentro de su empresa."""
    if not x_line_id:
        raise HTTPException(401, "Encabezado X-Line-Id ausente")
    return get_company_line(db, company, x_line_id)


def get_company_line(db: Session, company: Company, line_id: str) -> Line:
    # Filtrar por company_id en la consulta (no después) y responder 404 en vez de 403:
    # otra empresa no debe poder ni confirmar que la línea existe.
    line = db.scalar(select(Line).where(Line.id == line_id, Line.company_id == company.id))
    if line is None:
        raise HTTPException(404, "Línea no encontrada")
    return line
