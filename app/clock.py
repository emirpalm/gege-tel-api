from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

# Las reglas de negocio "vigente hoy" y "una vez al mes" se evalúan en hora de México,
# no en UTC: un canje el 31 a las 20:00 (CDMX) ya es 1 del mes siguiente en UTC.
BUSINESS_TZ = ZoneInfo("America/Mexico_City")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_naive(moment: datetime) -> datetime:
    """Normaliza a UTC sin tzinfo para guardar y comparar en SQLite de forma consistente."""
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def business_today(now: datetime) -> date:
    return now.astimezone(BUSINESS_TZ).date()


def business_period(now: datetime) -> str:
    return now.astimezone(BUSINESS_TZ).strftime("%Y-%m")
