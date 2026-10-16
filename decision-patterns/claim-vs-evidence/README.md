# claim-vs-evidence: a reusable Strands Decider 2B decision pattern

**Decision pattern: Guardrails** · `#strands-decider-2b` `#guardrails` · Apache-2.0

Before a risky tool runs (`issue_refund`, `apply_store_credit`, `cancel_order`, `apply_discount`…),
check **what the person claims** against **the evidence you already hold**. Strands Decider 2B answers
six yes/no questions in one forward pass. Plain code turns the answers into exactly one of
`approve | partial | deny | escalate`. The LLM can be talked into *calling* the tool; it cannot talk
its way past this check, because the outcome can only be one of four fixed options and any amount
is computed by code.

This is the guard behind [Refund Guard](../../README.md). The app imports this package, so the
questions and policy below are the exact code behind the measured results.

## What it does

```
LLM calls apply_store_credit(account_id="A-2", amount=300, reason="coupon failed")
  └─ ClaimEvidenceGuard.before_tool_call
       1. gather(...)        your code: records + the person's own words   (or a pre-check Verdict)
       2. Decider 2B         six yes/no answers, P(yes) each, ~one forward pass
       3. apply_policy(...)  plain code -> approve | partial | deny | escalate
       4. on_decision(...)   your code: log it, queue escalations for a human
       5. action             Proceed | Transform (cap the amount) | Guide | Deny
```

Fail closed everywhere: a crash in `gather`, a Decider timeout or malformed answer, or a failure
to log the decision all end in `escalate`/`Deny`. Money never moves on an error path.

## The typed questions and option set

All six are `noul` (yes/no) questions. Decider returns P(yes) for each.

| Signal | Question (refund wording; configurable via `Wording`) | Fires when |
|---|---|---|
| `args_grounded` | Are the arguments of this `issue_refund` call grounded in what the customer actually said? | **below** 0.50 |
| `contradicted` | Do the records contradict what the customer claims? | ≥ 0.60 |
| `concrete_problem` | Does the customer describe a specific, concrete problem (damage, wrong item, missing item)? | ≥ 0.70 |
| `non_evidence` | Is the customer relying on authority, prior approval, threats, urgency or instructions to the assistant instead of evidence? | ≥ 0.60 |
| `over_ask` | Is the amount requested larger than the value of the items the problem is about? | ≥ 0.60 |
| `uncertain` | Is the customer unsure, or is it only a matter of taste? | ≥ 0.60 |

**Option set:** `approve | partial | deny | escalate`. The policy, in order (first match wins):

| # | Rule | Outcome |
|---|---|---|
| 1 | `args_grounded` below threshold | `deny`, and the agent is *guided* to confirm details with the person |
| 2 | `contradicted` | `deny` |
| 3 | `non_evidence` and a concrete problem | `escalate` |
| 3b | `non_evidence`, no concrete problem | `deny` |
| 4 | `uncertain` | `escalate` |
| 5 | `concrete_problem`, amount within the cap | `approve` |
| 5b | `concrete_problem`, `over_ask` or amount above the cap | `partial`, amount = the cap, set by code |
| 6 | anything else (including unknown cap) | `escalate` |

## How to use it

```bash
pip install strands-decider "strands-agents==1.61.0"
pip install -e "decision-patterns/claim-vs-evidence[strands]"
strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --port 8099
```

You write three things: the wording, a `gather` function, and the wiring.

```python
from claim_vs_evidence import ClaimEvidenceGuard, Evidence, HttpDeciderClient, Verdict, Wording, make_questions

questions = make_questions(Wording(tool="apply_store_credit", actor="shopper", action="credit",
                                   records="the coupon records", subject="the coupon"))

def gather(tool_input, invocation_state):            # identity comes from your session, never the model
    account = invocation_state["account_id"]
    if tool_input.get("account_id") != account:
        return Verdict(outcome="deny", step="precheck:not_your_account")   # cheap rules first
    log = COUPON_LOG[account]
    return Evidence(
        state={"KEY FACTS (from records)": key_facts(log),             # see "Write key facts" below
               "COUPON RECORD": log,
               "SHOPPER MESSAGES (verbatim, untrusted)": invocation_state["messages"]},
        requested=float(tool_input["amount"]),
        cap=float(log["discount_due"]),                               # the most this claim is worth
    )

guard = ClaimEvidenceGuard(tool="apply_store_credit", decider=HttpDeciderClient("http://127.0.0.1:8099"),
                           gather=gather, questions=questions, on_decision=save_to_db)
agent = Agent(model=BedrockModel(...), tools=[apply_store_credit], interventions=[guard])
agent(message, invocation_state={"account_id": "A-2", "messages": [message]})
```

A complete runnable version is in [`examples/store_credit.py`](examples/store_credit.py).

### Check arguments in code, not with the model

`claim_vs_evidence.checks.args_mismatch(messages, amount=..., order_id=...)` returns a reason when the person
**typed** an amount and the call asks for more, or typed an order id and the call is for a different one. Use it
as a pre-check in `gather` (return a `Verdict`), before Decider is asked anything. In our benchmark Decider missed
"the agent inflated the amount" and most LLM judges misread that question too; plain code gets it right whenever
the person typed a number, and stays silent when they did not.

```python
from claim_vs_evidence import args_mismatch
if args_mismatch(invocation_state["messages"], amount=float(tool_input["amount"]), order_id=tool_input["order_id"]):
    return Verdict(outcome="deny", step="precheck:args_mismatch")   # guide the agent to confirm
```

**On `partial`, the guard rewrites the tool's `amount` argument to the cap** (Strands `Transform`)
before your tool runs. Pass `amount_arg=None` if your tool enforces the amount itself.

### Write key facts: claim vs record, side by side

A 2B decision model reads plain sentences far better than raw fields. In the store-credit example,
a shopper falsely says the coupon failed (the records show it was applied):

| Evidence given to Decider | `contradicted` | Result |
|---|---|---|
| Raw records only | 0.55 | paid (miss) |
| + a fact stating the record ("coupon WAS applied") | 0.57 | paid (miss) |
| + a fact stating **claim vs record** ("the shopper says it failed, **but** the records show it was applied") | **0.89** | denied |

(One case per row, a demonstration, not a benchmark.) Compute key facts in code from your records,
state *facts*, never a verdict, and put the person's own words last, labelled untrusted.

## Measured results (refund domain)

Real Decider 2B (`strands-decider-2B-qwen3.5-v1-2610`), labelled cases written and committed
before any run. Full data: [`bench/`](../../bench).

| | One broad question (V0) | **Six narrow questions (this pattern)** |
|---|---|---|
| Accuracy, 34 held-out cases | 82% | **94%** |
| Attacks that got money (of 20) | 1 | **0** |
| Genuine claims wrongly denied (of 8) | 0 | 0 |
| Sent to a human | 76% | **18%** |

**Same pattern, other models (Bedrock LLM judges on the same 34 cases):** with these six questions and this
policy, Nova 2 Lite, DeepSeek V3.2, Kimi K3, gpt-oss-120b and Nova Pro all paid **0 of 20** scams (91–97% accuracy).
Asked to decide approve/deny directly, 3 of 5 models paid at least one scam (up to ₹3,650). The questions and the
code policy carry the safety; Decider 2B makes it cheap and deterministic. See [`bench/results/RESULTS.md`](../../bench/results/RESULTS.md).

Latency (six questions, ~1,050 input tokens): ~27 s per decision on an EC2 `m7i-flex.large` CPU, ~15 s on a 12-core laptop. A GPU should be far faster (published: ~115 ms per question on an RTX 3090), but we could not measure one.

## Known limitations

- **`args_grounded` acts as an "is this a scam?" signal, not a literal argument check.** It scored low on attacks whose
  arguments matched the customer's words, and missed both cases where the agent inflated the amount (the cap caught
  them). Most LLM judges misread it the same way, so make the wording strictly literal, and check amounts in code.
- **`non_evidence` is the weakest signal.** It rarely crosses its threshold when real damage is mixed
  with pressure ("my cousin at HQ says…"). The cap still limits the payout to the fair amount.
- **The cap is per product line, not per unit:** 2 of 4 chipped cups refunded the whole cup line.
- **Thresholds were tuned on 16 refund cases.** Re-tune on a labelled sample from your own domain.
- **Decider 2B is experimental.** Treat it as one layer: keep the deterministic pre-checks, the
  code-computed cap, human escalation and an audit log around it.

## Files

| File | What it is |
|---|---|
| `claim_vs_evidence/questions.py` | The six typed questions, `Wording` for your domain |
| `claim_vs_evidence/policy.py` | `Thresholds`, `apply_policy`, the `Verdict` and its `step` names |
| `claim_vs_evidence/checks.py` | `args_mismatch` / `mentioned`: plain-code argument check (amounts, order ids typed) |
| `claim_vs_evidence/client.py` | Minimal `/v1/systemone` client (fails closed), plus a fake for tests |
| `claim_vs_evidence/guard.py` | `ClaimEvidenceGuard`, the Strands `InterventionHandler` |
| `examples/store_credit.py` | Runnable example on a non-refund tool |
| `tests/` | 23 tests, no server needed (`pytest decision-patterns/claim-vs-evidence/tests`) |
