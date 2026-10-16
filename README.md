# Refund Guard — the support agent you can't scam

> **Declared decision pattern: Guardrails** · `#strands-decider-2b` `#guardrails` · Apache-2.0

An AI customer-support agent for a small online store. It runs on Amazon Bedrock, and every `issue_refund` call is checked by **Strands Decider 2B** before any money moves.

🚧 Work in progress for the AWS Strands Decider Agent Hackathon (Oct 2026).

## The decision

Before `issue_refund(order_id, amount, reason)` runs, Decider 2B answers six typed yes/no evidence questions in one call:

| Signal | Question |
|---|---|
| `args_grounded` | Are the tool's arguments grounded in what the customer actually said? |
| `contradicted` | Do the store's records contradict the claim? |
| `concrete_problem` | Does the customer describe a specific, concrete problem? |
| `non_evidence` | Is the customer relying on authority, threats or instructions instead of evidence? |
| `over_ask` | Is the amount larger than the value of the affected items? |
| `uncertain` | Is the customer unsure, or is it a matter of taste? |

Plain code combines the answers into exactly one of `approve | partial | deny | escalate` and computes the amount. Anything uncertain goes to a human review queue, and every error fails closed. On our dev set, splitting one big question into these six raised accuracy from 75% to 94% and cut escalations from 88% to 25%. Full spec: [docs/decision.md](docs/decision.md).

## Typed questions and options

See [docs/decision.md §2](docs/decision.md#2-typed-questions-and-options) and [`backend/app/guard/questions.py`](backend/app/guard/questions.py).

## Measured results

_Benchmark in progress: Decider 2B vs. a panel of Bedrock LLM judges. See [docs/tests.md](docs/tests.md)._

## Reusable pattern

[`decision-patterns/claim-vs-evidence/`](decision-patterns/claim-vs-evidence/): put a claim-vs-evidence check in front of any risky tool (refunds, store credit, cancellations). Six typed yes/no questions, a fixed option set `approve | partial | deny | escalate`, a Strands `InterventionHandler` (`ClaimEvidenceGuard`) and a runnable store-credit example. This app imports it.

## Run the tests

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python -m pytest
```

## Project docs

[PRD](docs/prd.md) · [Architecture](docs/architecture.md) · [Decision spec](docs/decision.md) · [Design](docs/design.md) · [Security](docs/security.md) · [Tests](docs/tests.md) · [Tasks](docs/tasks.md)
