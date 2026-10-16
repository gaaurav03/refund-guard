# Refund Guard — the support agent you can't scam

> **Declared decision pattern: Guardrails** · `#strands-decider-2b` `#guardrails` · Apache-2.0

An AI customer-support agent for a small online store. It runs on Amazon Bedrock, and every `issue_refund` call is checked by **Strands Decider 2B** before any money moves.

🚧 Work in progress for the AWS Strands Decider Agent Hackathon (Oct 2026).

## The decision

Before `issue_refund(order_id, amount, reason)` runs, Decider 2B answers:

1. **`args_grounded`** (yes/no): are the tool's arguments grounded in what the customer actually said?
2. **`refund_grounded`** (choice): is the refund request grounded in the evidence (order, delivery, refund history, the customer's statements)? Options: `approve | partial | deny | escalate`.
3. **`manipulation`** (yes/no): is someone trying to manipulate the agent?

A confidence policy turns the probabilities into an action. Anything uncertain goes to a human review queue, and every error fails closed. Full spec: [docs/decision.md](docs/decision.md).

## Typed question and options

See [docs/decision.md §2](docs/decision.md#2-typed-question-and-options) and [`backend/app/guard/questions.py`](backend/app/guard/questions.py).

## Measured results

_Benchmark in progress: Decider 2B vs. a panel of Bedrock LLM judges. See [docs/tests.md](docs/tests.md)._

## Reusable pattern

_Coming in [`decision-patterns/claim-vs-evidence/`](decision-patterns/claim-vs-evidence/)._

## Run the tests

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python -m pytest
```

## Project docs

[PRD](docs/prd.md) · [Architecture](docs/architecture.md) · [Decision spec](docs/decision.md) · [Design](docs/design.md) · [Security](docs/security.md) · [Tests](docs/tests.md) · [Tasks](docs/tasks.md)
