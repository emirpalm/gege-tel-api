from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

Plan = Literal["basic", "premium"]


class LineCreate(BaseModel):
    employee_name: str = Field(min_length=1)
    phone_number: str = Field(pattern=r"^\d{10}$")
    plan: Plan


class LineUpdate(BaseModel):
    plan: Plan


class LineOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    company_id: str
    employee_name: str
    phone_number: str
    plan: Plan
    status: str


class NetworkEventIn(BaseModel):
    event_id: str = Field(min_length=1)
    line_id: str = Field(min_length=1)
    type: Literal["activated", "suspended", "reactivated"]
    timestamp: AwareDatetime  # exige zona horaria: un timestamp sin zona es ambiguo para ordenar eventos


class NetworkEventOut(BaseModel):
    event_id: str
    result: Literal["applied", "ignored_stale", "duplicate"]
    line_status: str


class BenefitOut(BaseModel):
    """Sin promo_code: el código solo se entrega al canjear."""

    model_config = {"from_attributes": True}

    id: str
    category: str
    merchant: str
    description: str


class RedemptionOut(BaseModel):
    benefit_id: str
    merchant: str
    code: str
    period: str
    redeemed_at: datetime


class AgentQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AgentAnswer(BaseModel):
    answer: str
    benefits: list[BenefitOut]
    selector: str
