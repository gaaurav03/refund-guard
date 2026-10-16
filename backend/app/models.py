"""Canonical typed models. Field names match docs/decision.md section 3 exactly.

The TypeScript mirror lives in frontend/src/types/decision.ts.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Outcome = Literal["approve", "partial", "deny", "escalate"]
OUTCOMES: tuple[Outcome, ...] = ("approve", "partial", "deny", "escalate")

DecidedBy = Literal["precheck", "decider", "policy", "fallback", "human"]

DeliveryStatus = Literal["not_shipped", "in_transit", "delivered", "lost", "returned"]
ReturnWindowStatus = Literal["open", "closed"]
ClaimedReason = Literal[
    "damaged", "not_delivered", "wrong_item", "missing_item", "not_as_described", "changed_mind", "other"
]

MAX_QUOTES = 5
MAX_QUOTE_CHARS = 300
MAX_RECENT_MESSAGES = 6
MAX_MESSAGE_CHARS = 500


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OrderItem(_Strict):
    sku: str
    name: str
    qty: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class RefundClaimState(_Strict):
    """Everything Decider sees about one issue_refund call."""

    order_id: str
    customer_id: str
    items: list[OrderItem]
    order_amount: float = Field(ge=0)
    currency: str = "INR"
    order_date: date
    delivery_status: DeliveryStatus
    delivered_at: datetime | None = None
    proof_of_delivery: bool
    return_window_days: int = Field(default=30, ge=0)
    return_window_status: ReturnWindowStatus
    account_age_days: int = Field(ge=0)
    past_refund_count: int = Field(ge=0)
    past_refund_total: float = Field(ge=0)
    claimed_reason: ClaimedReason
    claimed_skus: list[str] = Field(default_factory=list)
    customer_quotes: list[str] = Field(default_factory=list, max_length=MAX_QUOTES)
    requested_amount: float
    tool_reason: str = ""
    recent_customer_messages: list[str] = Field(default_factory=list, max_length=MAX_RECENT_MESSAGES)

    @field_validator("customer_quotes")
    @classmethod
    def _quote_length(cls, v: list[str]) -> list[str]:
        if any(len(q) > MAX_QUOTE_CHARS for q in v):
            raise ValueError(f"each quote must be at most {MAX_QUOTE_CHARS} characters")
        return v

    @field_validator("recent_customer_messages")
    @classmethod
    def _message_length(cls, v: list[str]) -> list[str]:
        if any(len(m) > MAX_MESSAGE_CHARS for m in v):
            raise ValueError(f"each message must be at most {MAX_MESSAGE_CHARS} characters")
        return v


class DeciderResult(_Strict):
    """Normalised answer from /v1/systemone: P(yes) for each evidence question (see guard/questions.py)."""

    signals: dict[str, float]
    latency_ms: float = 0.0


class Decision(_Strict):
    """Final verdict for one issue_refund call, after pre-checks, Decider and policy."""

    outcome: Outcome
    approved_amount: float = 0.0
    decided_by: DecidedBy
    policy_step: str
    rule_id: str | None = None
    decider: DeciderResult | None = None
    agent_feedback: str = ""
