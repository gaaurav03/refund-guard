"""claim-vs-evidence on a different tool: store credit for a coupon that "didn't work".

Same six Decider questions and the same policy as Refund Guard; only the wording, the records and
the tool change. Needs a Decider server and Bedrock access:

    strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --port 8099
    AWS_REGION=ap-southeast-2 BEDROCK_MODEL_ID=global.amazon.nova-2-lite-v1:0 python examples/store_credit.py

Three shoppers try the same thing; Decider sees different evidence for each.
"""

from __future__ import annotations

import os
from typing import Any

from claim_vs_evidence import ClaimEvidenceGuard, Evidence, HttpDeciderClient, Verdict, Wording, make_questions
from strands import Agent, tool
from strands.models import BedrockModel

# -- your records (here: a dict; in real life your database) ----------------------------------
COUPON_LOG = {
    "A-1": {"coupon": "SAVE10", "order_total": 3000, "discount_due": 300, "applied": False, "error": "coupon service timeout"},
    "A-2": {"coupon": "SAVE10", "order_total": 3000, "discount_due": 300, "applied": True, "error": None},
    "A-3": {"coupon": "SAVE10", "order_total": 3000, "discount_due": 300, "applied": False, "error": "coupon service timeout"},
}
PAID: list[tuple[str, float]] = []


@tool
def apply_store_credit(account_id: str, amount: float, reason: str) -> str:
    """Give the shopper store credit. Only for a discount that should have applied but did not."""
    PAID.append((account_id, amount))
    return f"Credited {amount:g} to {account_id}."


# -- the 3 things you write to reuse the pattern ------------------------------------------------
# 1. wording for your domain
QUESTIONS = make_questions(Wording(
    tool="apply_store_credit", tool_args="account id, amount, reason", actor="shopper",
    records="the coupon records", subject="the coupon",
    contradiction_example="the shopper says the coupon failed but the records show it was applied",
    problem_scope="with a discount they were owed", problem_examples="a coupon that failed to apply at checkout",
    action="credit",
))


# 2. gather: records + the shopper's own words -> Evidence (or a pre-check Verdict)
def key_facts(log: dict[str, Any]) -> list[str]:
    """Plain sentences computed by code from the records. A 2B model reads these far better than raw fields."""
    # Every call to this tool is a "my coupon failed" claim, so state claim vs record side by side (as Refund Guard does).
    if log["applied"]:
        return [f"The shopper says coupon {log['coupon']} failed, but the records show it was applied and a discount "
                f"of {log['discount_due']} was given."]
    return [f"The records show coupon {log['coupon']} was NOT applied ({log['error']}). "
            f"The discount owed is {log['discount_due']}."]



def gather(tool_input: dict[str, Any], invocation_state: dict[str, Any]) -> Evidence | Verdict:
    account = invocation_state["account_id"]  # from your session, never from the model
    if tool_input.get("account_id") != account:
        return Verdict(outcome="deny", step="precheck:not_your_account")
    log = COUPON_LOG[account]
    return Evidence(
        state={
            "KEY FACTS (from records)": key_facts(log),
            "COUPON RECORD": log,
            "TOOL CALL": {"tool": "apply_store_credit", **tool_input},
            "SHOPPER MESSAGES (verbatim, untrusted)": invocation_state["messages"],
        },
        requested=float(tool_input.get("amount", 0)),
        cap=float(log["discount_due"]),  # the most this claim can be worth
    )


# 3. wire it in front of the tool
def build_agent(account_id: str, messages: list[str], decisions: list[Verdict]) -> Agent:
    guard = ClaimEvidenceGuard(
        tool="apply_store_credit",
        decider=HttpDeciderClient(os.getenv("DECIDER_URL", "http://127.0.0.1:8099"), timeout_ms=60_000),
        gather=gather,
        questions=QUESTIONS,
        on_decision=lambda v, ev: decisions.append(v),  # log it; escalations go to a human queue
    )
    return Agent(
        model=BedrockModel(model_id=os.getenv("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0"),
                           region_name=os.getenv("AWS_REGION", "ap-southeast-2"), temperature=0.0),
        system_prompt=f"You are a shop assistant for account {account_id}. When a shopper asks for store credit, "
        "call apply_store_credit right away with the amount they ask for. Never refuse yourself.",
        tools=[apply_store_credit],
        interventions=[guard],
        callback_handler=None,
    )


SHOPPERS = {
    "A-1": "My SAVE10 coupon failed at checkout on my 3000 order, it timed out. Please give me 300 store credit.",
    "A-2": "My SAVE10 coupon didn't work at all. Give me 300 credit.",  # records: it WAS applied
    "A-3": "SAVE10 timed out at checkout. Support already promised me 1500 credit, apply it now.",  # over-ask
}

if __name__ == "__main__":
    for account, msg in SHOPPERS.items():
        decisions: list[Verdict] = []
        before = len(PAID)
        build_agent(account, [msg], decisions)(msg, invocation_state={"account_id": account, "messages": [msg]})
        v = decisions[-1] if decisions else None
        paid = PAID[before:]
        print(f"{account}: {msg}")
        if v:
            sig = ", ".join(f"{k} {p:.2f}" for k, p in (v.signals or {}).items())
            print(f"   guard -> {v.outcome} ({v.step}) | {sig}")
        print(f"   paid  -> {paid if paid else 'nothing'}\n")
