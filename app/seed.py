from datetime import date

from sqlalchemy.orm import Session

from app.models import Benefit, Company, Line

COMPANIES = [
    Company(id="acme", name="Acme"),
    Company(id="globex", name="Globex"),
]

BOTH = "basic,premium"

CATALOG = [
    Benefit(id="B1", category="Restaurantes", merchant="La Parrilla", description="20% de descuento", promo_code="PARR20", plans=BOTH),
    Benefit(id="B2", category="Restaurantes", merchant="Sushi Go", description="2x1", promo_code="SUSHI2X1", plans="premium"),
    Benefit(id="B3", category="Restaurantes", merchant="Café Luna", description="$50 de descuento", promo_code="LUNA50", plans=BOTH, valid_until=date(2026, 9, 30)),
    Benefit(id="B4", category="Cine", merchant="Cine Plaza", description="2x1 los martes", promo_code="CINE2X1", plans=BOTH),
    Benefit(id="B5", category="Restaurantes", merchant="Tacos El Güero", description="15% de descuento", promo_code="GUERO15", plans="basic"),
    Benefit(id="B6", category="Gimnasio", merchant="FitZone", description="Un mes gratis", promo_code="FIT1MES", plans="premium"),
]

# Líneas de ejemplo para la demo (L-100 es la del ejemplo de webhook del enunciado).
DEMO_LINES = [
    Line(id="L-100", company_id="acme", employee_name="Ana Acme", phone_number="5510000100", plan="basic"),
    Line(id="L-200", company_id="globex", employee_name="Gael Globex", phone_number="5510000200", plan="premium"),
]


def seed(db: Session, demo_lines: bool = False) -> None:
    rows = COMPANIES + CATALOG + (DEMO_LINES if demo_lines else [])
    for row in rows:
        # merge = insert-or-update; permite reiniciar sin duplicar.
        db.merge(row)
    db.commit()
