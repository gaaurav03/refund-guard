"""FastAPI app: chat, "Try to scam our bot" challenge, live decisions, scoreboard, review queue.

Routes match docs/architecture.md section 4. Dependencies are injected so tests run without
Bedrock or a Decider server.
"""

from __future__ import annotations

import contextlib
import hmac
import html
import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .agent.session import Session
from .config import Settings
from .guard.questions import QUESTIONS
from .security.limits import Limits, ip_hash
from .store import seed_data
from .store.repo import Repo

log = logging.getLogger(__name__)

SESSION_TTL_S = 2 * 60 * 60
MAX_LIVE_SESSIONS = 500

# Converts one agent turn's Bedrock usage into USD. TODO-VERIFY (TV-13): set from the chosen model's price.
PRICE_IN_PER_1K_USD = 0.0002
PRICE_OUT_PER_1K_USD = 0.0008
EXTRACTION_TOKENS_ESTIMATE = (700, 120)  # one extraction call per refund attempt

SIGNAL_LABELS = {
    "args_grounded": "Arguments grounded in what the customer said",
    "contradicted": "Records contradict the claim",
    "concrete_problem": "Concrete problem described",
    "non_evidence": "Pressure or instructions instead of evidence",
    "over_ask": "Asks for more than the affected items",
    "uncertain": "Customer unsure / matter of taste",
}

POLICY_STEP_LABELS = {
    "decider:args_ungrounded": "Refund arguments don't match what the customer said",
    "decider:contradicted": "Store records contradict the claim",
    "decider:pressure_with_problem": "Real problem, but with pressure: a human checks",
    "decider:non_evidence": "Pressure or instructions instead of evidence",
    "decider:uncertain": "Customer is unsure: a human checks",
    "decider:partial": "Real problem with some items: refund capped to those items",
    "decider:approve": "Concrete problem, nothing contradicts it",
    "policy:no_items_identified": "No item identified: a human checks",
    "policy:no_concrete_problem": "No concrete problem established: a human checks",
    "policy:repeated_confirmations": "Repeated attempts after being asked to confirm: a human checks",
}

PRECHECK_LABELS = {
    "PC-01": "Order not found",
    "PC-02": "Order belongs to someone else",
    "PC-03": "Amount is zero or larger than the order",
    "PC-04": "Order already refunded",
    "PC-05": "Claimed item is not in the order",
    "PC-06": "Return window closed (changed mind)",
    "PC-07": "Return window closed: a human checks",
    "PC-08": "High-value refund: a human checks",
    "PC-09": "Order still in transit",
    "PC-10": "Amount or order differs from what the customer typed",
}

AgentFactory = Callable[[Session], Any]  # returns a callable agent: agent(msg, invocation_state=...) -> result


@dataclass
class LiveSession:
    session: Session
    agent: Any
    ip_key: str
    created: float = field(default_factory=time.time)
    messages: int = 0


# ---------- request / response models


class CreateSession(BaseModel):
    customer_id: str
    mode: Literal["chat", "challenge"] = "chat"
    gullible: bool = False


class SessionOut(BaseModel):
    session_id: str
    customer_id: str
    mode: str
    gullible: bool
    max_messages: int


class ChatIn(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=1000)


class ChatOut(BaseModel):
    reply: str
    decisions: list[dict[str, Any]]
    messages_left: int


class ReviewAction(BaseModel):
    action: Literal["approve", "deny"]
    amount: float | None = None
    note: str = Field(default="", max_length=500)


# ---------- helpers


def _snippet(text: str, n: int = 40) -> str:
    clean = html.escape(" ".join(text.split()))
    return clean if len(clean) <= n else clean[: n - 1] + "…"


def _turn_cost_usd(result: Any, refund_attempts: int) -> float:
    usage: dict[str, int] = {}
    with contextlib.suppress(AttributeError, TypeError):
        usage = dict(result.metrics.accumulated_usage)
    tin = usage.get("inputTokens", 0) + refund_attempts * EXTRACTION_TOKENS_ESTIMATE[0]
    tout = usage.get("outputTokens", 0) + refund_attempts * EXTRACTION_TOKENS_ESTIMATE[1]
    return tin / 1000 * PRICE_IN_PER_1K_USD + tout / 1000 * PRICE_OUT_PER_1K_USD


def personas() -> list[dict[str, Any]]:
    orders_by_customer: dict[str, list[dict[str, Any]]] = {}
    for o in seed_data.ORDERS:
        orders_by_customer.setdefault(o["customer_id"], []).append({
            "order_id": o["order_id"],
            "order_date": o["order_date"],
            "items": [{"name": i["name"], "qty": i["qty"], "unit_price": i["unit_price"]} for i in o["items"]],
            "order_amount": seed_data.order_amount(o),
        })
    return [{"customer_id": c["customer_id"], "name": c["name"], "label": c["persona_label"],
             "orders": orders_by_customer.get(c["customer_id"], [])} for c in seed_data.CUSTOMERS]


def create_app(*, settings: Settings, repo: Repo, agent_factory: AgentFactory,
               decider_health: Callable[[], dict[str, Any]] | None = None,
               ip_salt: str | None = None) -> FastAPI:
    app = FastAPI(title="Refund Guard", version="0.1.0")
    limits = Limits(per_min_ip=settings.rate_limit_per_min_ip,
                    sessions_per_ip_day=settings.max_sessions_per_ip_day,
                    daily_budget_usd=settings.daily_bedrock_budget_usd)
    salt = ip_salt or uuid.uuid4().hex
    sessions: dict[str, LiveSession] = {}
    lock = threading.Lock()
    known_customers = {c["customer_id"] for c in seed_data.CUSTOMERS}

    def client_key(request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
        return ip_hash(ip, salt)

    def rate_limit(request: Request) -> str:
        key = client_key(request)
        if not limits.allow_request(key):
            raise HTTPException(429, "Too many requests. Please slow down.")
        return key

    def evict_expired() -> None:
        now = time.time()
        for sid in [s for s, live in sessions.items() if now - live.created > SESSION_TTL_S]:
            sessions.pop(sid, None)

    def require_reviewer(token: str | None) -> None:
        if not settings.reviewer_token:
            raise HTTPException(503, "Review queue is disabled (no REVIEWER_TOKEN configured).")
        if not token or not hmac.compare_digest(token, settings.reviewer_token):
            raise HTTPException(401, "Invalid reviewer token.")

    # ---------- routes

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        decider: dict[str, Any]
        try:
            decider = {"ok": True, **(decider_health() if decider_health else {})}
        except Exception as e:
            decider = {"ok": False, "error": type(e).__name__}
        return {"ok": True, "decider": decider, "budget_exhausted": limits.budget_exhausted(),
                "spend_today_usd": limits.spend_today()}

    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        thresholds = {
            "args_grounded": settings.args_grounded_threshold,
            "contradicted": settings.contradicted_threshold,
            "concrete_problem": settings.concrete_problem_threshold,
            "non_evidence": settings.non_evidence_threshold,
            "over_ask": settings.over_ask_threshold,
            "uncertain": settings.uncertain_threshold,
        }
        return {
            "signals": [{"name": n, "label": SIGNAL_LABELS[n], "instructions": QUESTIONS[n]["instructions"],
                         "threshold": thresholds[n], "fires_when": "below" if n == "args_grounded" else "above"}
                        for n in QUESTIONS],
            "policy_steps": POLICY_STEP_LABELS,
            "rules": PRECHECK_LABELS,
            "max_messages": settings.max_messages_per_session,
        }

    @app.get("/api/personas")
    def list_personas() -> list[dict[str, Any]]:
        return personas()

    @app.post("/api/sessions", response_model=SessionOut)
    def create_session(body: CreateSession, request: Request) -> SessionOut:
        key = rate_limit(request)
        if body.customer_id not in known_customers:
            raise HTTPException(404, "Unknown persona.")
        if limits.budget_exhausted():
            raise HTTPException(503, "The demo has used today's budget. Please come back tomorrow.")
        if not limits.allow_new_session(key):
            raise HTTPException(429, "Daily session limit reached for this network.")
        session = Session(customer_id=body.customer_id, mode=body.mode, gullible=body.gullible)
        with lock:
            evict_expired()
            if len(sessions) >= MAX_LIVE_SESSIONS:
                raise HTTPException(503, "The demo is busy. Please try again in a few minutes.")
            sessions[session.session_id] = LiveSession(session, agent_factory(session), key)
        return SessionOut(session_id=session.session_id, customer_id=session.customer_id, mode=session.mode,
                          gullible=session.gullible, max_messages=settings.max_messages_per_session)

    @app.post("/api/chat", response_model=ChatOut)
    def chat(body: ChatIn, request: Request) -> ChatOut:
        rate_limit(request)
        with lock:
            live = sessions.get(body.session_id)
        if live is None:
            raise HTTPException(404, "Session expired. Please start a new one.")
        if live.messages >= settings.max_messages_per_session:
            raise HTTPException(429, "Message limit reached for this session.")
        if limits.budget_exhausted():
            raise HTTPException(503, "The demo has used today's budget. Please come back tomorrow.")

        live.messages += 1
        session = live.session
        session.add_customer_message(body.message)
        seen = len(session.decisions)
        try:
            result = live.agent(body.message, invocation_state={"session": session})
            reply = str(result).strip()
        except Exception:
            log.exception("agent turn failed")
            result, reply = None, "Sorry, something went wrong on our side. A person from our team will follow up."

        new = session.decisions[seen:]
        for d in new:
            extra: dict[str, Any] = {"snippet": _snippet(body.message)}
            if d["outcome"] in ("approve", "partial"):
                order = repo.get_order(d["order_id"]) or {}
                truth = float(order.get("truth_refundable_amount", 0.0))
                extra["is_scam_success"] = d["approved_amount"] > truth + 0.01
            else:
                extra["is_scam_success"] = False
            d.update(extra)
            try:
                repo.update_decision(d["decision_id"], extra)
            except Exception:
                log.exception("could not annotate decision %s", d["decision_id"])
        limits.add_spend(_turn_cost_usd(result, len(new)))
        return ChatOut(reply=reply, decisions=new,
                       messages_left=settings.max_messages_per_session - live.messages)

    @app.get("/api/decisions/live")
    def live_decisions(since: str = "", limit: int = 20) -> list[dict[str, Any]]:
        rows = [d for d in repo.list_decisions() if d.get("source") == "challenge" and d.get("created_at", "") > since]
        rows.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        keep = ("decision_id", "created_at", "order_id", "requested_amount", "outcome", "approved_amount",
                "decided_by", "policy_step", "rule_id", "signals", "key_facts", "gullible", "snippet",
                "is_scam_success", "decision_latency_ms")
        return [{k: d.get(k) for k in keep} for d in rows[: max(1, min(limit, 100))]]

    @app.get("/api/scoreboard")
    def scoreboard() -> dict[str, int]:
        rows = [d for d in repo.list_decisions() if d.get("source") == "challenge"]
        return {
            "attempts": len(rows),
            "denied": sum(d["outcome"] == "deny" for d in rows),
            "escalated": sum(d["outcome"] == "escalate" for d in rows),
            "paid_genuine": sum(d["outcome"] in ("approve", "partial") and not d.get("is_scam_success") for d in rows),
            "scams_succeeded": sum(bool(d.get("is_scam_success")) for d in rows),
        }

    @app.get("/api/review")
    def review_queue(x_reviewer_token: str | None = Header(default=None)) -> list[dict[str, Any]]:
        require_reviewer(x_reviewer_token)
        items = repo.list_reviews(status="pending")
        items.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return items

    @app.post("/api/review/{decision_id}")
    def resolve_review(decision_id: str, body: ReviewAction,
                       x_reviewer_token: str | None = Header(default=None)) -> dict[str, Any]:
        require_reviewer(x_reviewer_token)
        item = repo.get_review(decision_id)
        if item is None:
            raise HTTPException(404, "Review item not found.")
        if item.get("status") != "pending":
            raise HTTPException(409, "Already resolved.")
        now = datetime.now(UTC).isoformat()
        paid = 0.0
        if body.action == "approve":
            requested = float(item.get("requested_amount", 0.0))
            paid = round(requested if body.amount is None else body.amount, 2)
            if not 0 < paid <= requested:
                raise HTTPException(422, f"Amount must be between 0 and the requested {requested:g} INR.")
            repo.put_refund({"customer_id": item["customer_id"], "refund_id": f"RF-{uuid.uuid4().hex[:10]}",
                             "order_id": item["order_id"], "amount": paid, "reason": f"human review: {body.note}"[:300],
                             "created_at": now, "simulated": True, "decision_id": decision_id})
        status = "approved" if body.action == "approve" else "denied"
        repo.update_review(decision_id, {"status": status, "reviewer_note": body.note, "resolved_at": now,
                                         "paid_amount": paid})
        repo.update_decision(decision_id, {"reviewed_outcome": status, "reviewed_amount": paid, "reviewed_at": now})
        return {"decision_id": decision_id, "status": status, "paid_amount": paid}

    return app
