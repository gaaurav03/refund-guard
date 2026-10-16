"""API tests with a stub agent that drives the REAL RefundGuard handler (fake Decider, in-memory data)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from app.agent.session import Session
from app.api import create_app
from app.config import Settings
from app.guard.decider_client import FakeDeciderClient, fake_payload
from app.guard.handler import RefundGuard
from app.guard.ledger import Ledger
from app.guard.policy import Thresholds
from app.store.repo import InMemoryRepo
from fastapi.testclient import TestClient

TOKEN = "test-reviewer-token"


class StubAgent:
    """Pretends to be the LLM: if the message contains 'refund ORD-x N', it calls issue_refund(ORD-x, N)."""

    def __init__(self, guard: RefundGuard) -> None:
        self.guard = guard
        self.calls = 0

    def __call__(self, msg: str, invocation_state: dict[str, Any]) -> str:
        words = msg.split()
        if "refund" in words and len(words) >= words.index("refund") + 3:
            i = words.index("refund")
            self.calls += 1
            event = SimpleNamespace(tool_use={"name": "issue_refund", "toolUseId": f"tu-{self.calls}",
                                              "input": {"order_id": words[i + 1], "amount": float(words[i + 2]),
                                                        "reason": "test"}},
                                    invocation_state=invocation_state)
            action = self.guard.before_tool_call(event)
            return f"guard said {type(action).__name__}"
        return "hello from the stub agent"


def make_extractor(skus: list[str]) -> Any:
    def extractor(system: str, user: str) -> str:
        return json.dumps({"claimed_reason": "damaged", "claimed_skus": skus, "customer_quotes": []})
    return extractor


def make_client(signals: dict[str, float] | None = None, skus: tuple[str, ...] = ("MUG-BLU",),
                **settings_overrides: Any) -> tuple[TestClient, InMemoryRepo]:
    repo = InMemoryRepo.seeded()
    ledger = Ledger()
    guard = RefundGuard(repo=repo, decider=FakeDeciderClient(lambda s, q: fake_payload(**(signals or {}))),
                        converse=make_extractor(list(skus)), ledger=ledger, thresholds=Thresholds(), high_value_escalate_inr=10000.0)
    settings = Settings(_env_file=None, reviewer_token=TOKEN, **settings_overrides)  # type: ignore[call-arg]

    def factory(session: Session) -> StubAgent:
        return StubAgent(guard)

    app = create_app(settings=settings, repo=repo, agent_factory=factory, decider_health=lambda: {"device": "fake"},
                     ip_salt="salt")
    return TestClient(app), repo


def start(client: TestClient, customer: str = "CUST-007", mode: str = "challenge", gullible: bool = True) -> str:
    r = client.post("/api/sessions", json={"customer_id": customer, "mode": mode, "gullible": gullible})
    assert r.status_code == 200, r.text
    return str(r.json()["session_id"])


def test_health_and_personas() -> None:
    client, _ = make_client()
    assert client.get("/api/health").json()["decider"]["ok"] is True
    people = client.get("/api/personas").json()
    asha = next(p for p in people if p["customer_id"] == "CUST-007")
    assert asha["orders"][0]["order_id"] in ("ORD-1042", "ORD-7008")
    assert "truth_refundable_amount" not in json.dumps(people)  # ground truth never leaves the server


def test_unknown_persona_rejected() -> None:
    client, _ = make_client()
    assert client.post("/api/sessions", json={"customer_id": "CUST-999"}).status_code == 404


def test_chat_returns_guard_decision_and_scoreboard_counts_it() -> None:
    client, _ = make_client()
    sid = start(client)
    r = client.post("/api/chat", json={"session_id": sid, "message": "please refund ORD-1042 450"})
    body = r.json()
    assert body["decisions"][0]["outcome"] == "approve"
    assert body["decisions"][0]["is_scam_success"] is False  # truth for ORD-1042 is 450
    board = client.get("/api/scoreboard").json()
    assert board == {"attempts": 1, "denied": 0, "escalated": 0, "paid_genuine": 1, "scams_succeeded": 0}


def test_scam_success_is_counted_honestly() -> None:
    # Decider (fake) wrongly approves a false claim on ORD-2077 whose true refundable amount is 0.
    client, _ = make_client(skus=("HAMPER-GFT",))
    sid = start(client, customer="CUST-011")
    client.post("/api/chat", json={"session_id": sid, "message": "refund ORD-2077 2400"})
    board = client.get("/api/scoreboard").json()
    assert board["scams_succeeded"] == 1
    live = client.get("/api/decisions/live").json()
    assert live[0]["is_scam_success"] is True
    assert live[0]["customer_name"] == "Ravi" and live[0]["tries"] == 1
    assert "snippet" not in live[0]  # visitor-written text is never in the public feed


def test_live_feed_escapes_html() -> None:
    client, _ = make_client(signals={"contradicted": 0.9}, skus=("HAMPER-GFT",))
    sid = start(client, customer="CUST-011")
    client.post("/api/chat", json={"session_id": sid, "message": "<script>x</script> refund ORD-2077 2400"})
    assert "<script>" not in client.get("/api/decisions/live").text


def test_message_cap() -> None:
    client, _ = make_client(max_messages_per_session=2)
    sid = start(client)
    for _ in range(2):
        assert client.post("/api/chat", json={"session_id": sid, "message": "hi"}).status_code == 200
    assert client.post("/api/chat", json={"session_id": sid, "message": "hi"}).status_code == 429


def test_message_length_limit() -> None:
    client, _ = make_client()
    sid = start(client)
    assert client.post("/api/chat", json={"session_id": sid, "message": "x" * 1001}).status_code == 422


def test_rate_limit_per_ip() -> None:
    client, _ = make_client(rate_limit_per_min_ip=3)
    codes = [client.get("/api/personas").status_code for _ in range(2)]
    codes += [client.post("/api/sessions", json={"customer_id": "CUST-007"}).status_code for _ in range(4)]
    assert 429 in codes


def test_sessions_per_day_cap() -> None:
    client, _ = make_client(max_sessions_per_ip_day=2)
    assert [client.post("/api/sessions", json={"customer_id": "CUST-007"}).status_code
            for _ in range(3)] == [200, 200, 429]


def test_budget_cap_blocks_new_sessions() -> None:
    client, _ = make_client(daily_bedrock_budget_usd=0.0)
    assert client.post("/api/sessions", json={"customer_id": "CUST-007"}).status_code == 503


def test_review_queue_requires_token() -> None:
    client, _ = make_client()
    assert client.get("/api/review").status_code == 401
    assert client.get("/api/review", headers={"x-reviewer-token": "wrong"}).status_code == 401


@pytest.mark.parametrize("action,amount,paid", [("approve", 300.0, 300.0), ("deny", None, 0.0)])
def test_escalation_flows_to_review_and_reviewer_resolves(action: str, amount: float | None, paid: float) -> None:
    client, repo = make_client(signals={"uncertain": 0.9})
    sid = start(client)
    decision = client.post("/api/chat", json={"session_id": sid, "message": "refund ORD-1042 450"}).json()["decisions"][0]
    assert decision["outcome"] == "escalate"
    h = {"x-reviewer-token": TOKEN}
    queue = client.get("/api/review", headers=h).json()
    assert [q["decision_id"] for q in queue] == [decision["decision_id"]]
    before = len(repo.refunds)
    r = client.post(f"/api/review/{decision['decision_id']}", headers=h, json={"action": action, "amount": amount})
    assert r.json()["paid_amount"] == paid
    assert len(repo.refunds) == before + (1 if action == "approve" else 0)
    assert client.get("/api/review", headers=h).json() == []
    assert client.post(f"/api/review/{decision['decision_id']}", headers=h,
                       json={"action": "deny"}).status_code == 409


def test_reviewer_cannot_pay_more_than_requested() -> None:
    client, _ = make_client(signals={"uncertain": 0.9})
    sid = start(client)
    did = client.post("/api/chat", json={"session_id": sid, "message": "refund ORD-1042 450"}).json()["decisions"][0][
        "decision_id"]
    r = client.post(f"/api/review/{did}", headers={"x-reviewer-token": TOKEN}, json={"action": "approve", "amount": 9999})
    assert r.status_code == 422


def test_meta_exposes_signals_thresholds_and_labels() -> None:
    client, _ = make_client()
    meta = client.get("/api/meta").json()
    names = [s["name"] for s in meta["signals"]]
    assert names == ["args_grounded", "contradicted", "concrete_problem", "non_evidence", "over_ask", "uncertain"]
    assert next(s for s in meta["signals"] if s["name"] == "args_grounded")["fires_when"] == "below"
    assert "decider:contradicted" in meta["policy_steps"] and "PC-03" in meta["rules"]


def test_decisions_carry_key_facts() -> None:
    client, _ = make_client()
    sid = start(client)
    d = client.post("/api/chat", json={"session_id": sid, "message": "refund ORD-1042 450"}).json()["decisions"][0]
    assert d["key_facts"] and isinstance(d["key_facts"][0], str)
    assert client.get("/api/decisions/live").json()[0]["key_facts"] == d["key_facts"]


def test_one_chat_is_one_attempt_however_many_tries() -> None:
    client, _ = make_client(signals={"contradicted": 0.9}, skus=("HAMPER-GFT",))
    sid = start(client, customer="CUST-011")
    for _ in range(3):
        client.post("/api/chat", json={"session_id": sid, "message": "refund ORD-2077 2400"})
    other = start(client)
    client.post("/api/chat", json={"session_id": other, "message": "please refund ORD-1042 450"})
    board = client.get("/api/scoreboard").json()
    assert board["attempts"] == 2
    live = client.get("/api/decisions/live").json()
    assert len(live) == 2
    assert sorted(item["tries"] for item in live) == [1, 3]
    assert "refund ORD-2077" not in client.get("/api/decisions/live").text
