# Refund Guard — the support agent you can't scam

> **Declared decision pattern: Guardrails** · `#strands-decider-2b` `#guardrails` · Apache-2.0

An AI customer-support agent for a small online store. It runs on Amazon Bedrock, and every `issue_refund` call is checked by **Strands Decider 2B** before any money moves.

| | |
|---|---|
| 🎥 **Demo video (under 3 min)** | https://youtu.be/l-mvH-7ydu0 |
| 🌐 **Live demo** | https://dl0e9zh1uq30l.cloudfront.net (the live agent runs during demo sessions; otherwise the page shows "demo sleeping" and the video) |
| 🧩 **Reusable pattern** | [`decision-patterns/claim-vs-evidence/`](decision-patterns/claim-vs-evidence/) |

Built for the AWS Strands Decider Agent Hackathon (Oct 2026).

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

Held-out test split: **34 cases**, labels committed before any run. Every arm gets the same evidence. Full table, prompts and raw rows are in [`bench/results/RESULTS.md`](bench/results/RESULTS.md).

**Arm 1: the model answers the six evidence questions; the same code decides outcome and amount**

| Model | Accuracy | Scams paid (of 20) | Genuine denied (of 8) | Escalated | Same answer every run | USD per 1k decisions |
|---|---|---|---|---|---|---|
| **Decider 2B** | 94% | **0** | 0 | 18% | yes (0 flips) | 0.89 (EC2 CPU, ~27 s each) |
| Nova 2 Lite | 97% | 0 | 1 | 18% | 1 flip | 0.45 |
| DeepSeek V3.2 | 91% | 0 | 1 | 18% | yes | 0.65 |
| Kimi K3 (1 run) | 97% | 0 | 1 | 18% | n/a | 15.46 |
| gpt-oss-120b | 91% | 0 | 1 | 12% | 3 flips | 0.39 |
| Nova Pro | 94% | 0 | 0 | 15% | yes | 0.92 |

**Arm 2: the model decides approve / partial / deny / escalate by itself**

| Model | Accuracy | Scams paid (of 20) |
|---|---|---|
| Nova 2 Lite (the agent's own chat model) | 76% | **2, ₹3,650 paid out** |
| gpt-oss-120b | 88% | 1, ₹2,400 |
| Nova Pro | 88% | 1, ₹2,400 |
| DeepSeek V3.2 | 91% | 0 |
| Kimi K3 (1 run) | 97% | 0 |

**What this shows**
- **The pattern is what keeps money safe.** With six narrow questions plus code deciding, *every* model paid 0 of 20 scams. Asking an LLM "should I refund?" directly paid scams for 3 of 5 models, including the agent's own model.
- **Decider 2B matches big LLMs on accuracy (94% vs 91–97%) but doesn't beat them.** Its case rests on bounded outputs and determinism. On our Free-plan CPU machine it is **slower** (~27 s vs 1–4 s) and about the same cost, so we do not claim a speed or cost win.
- **Honest misses:** `args_grounded` scored as an "is this a scam?" signal, not a literal argument check (68% vs its label; gpt-oss 92%, Kimi 94%). Most models misread it on attacks, so the wording is our fix to make. Decider also missed both "chatbot inflated the amount" cases, but the code cap paid only the item's value.
- Decider latency: **~27 s per decision on EC2 `m7i-flex.large`** (Free plan; GPUs are blocked), 14.6 s on a laptop CPU. LLM judges, measured one call at a time: Nova Pro 0.97 s, Nova 2 Lite 1.07 s, gpt-oss 2.1 s, DeepSeek 4.3 s, Kimi K3 21.8 s (median).

## Reusable pattern

[`decision-patterns/claim-vs-evidence/`](decision-patterns/claim-vs-evidence/): put a claim-vs-evidence check in front of any risky tool (refunds, store credit, cancellations). Six typed yes/no questions, a fixed option set `approve | partial | deny | escalate`, a Strands `InterventionHandler` (`ClaimEvidenceGuard`) and a runnable store-credit example. This app imports it.

## Run the tests

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python -m pytest
```

## Project docs

[PRD](docs/prd.md) · [Architecture](docs/architecture.md) · [Decision spec](docs/decision.md) · [Design](docs/design.md) · [Security](docs/security.md) · [Tests](docs/tests.md) · [Tasks](docs/tasks.md)
