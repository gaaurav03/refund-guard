# Builder Center submission: copy-paste sheet

Paste each block into the matching field of **Edit project**. Turn the **Markdown** toggle ON before pasting the Body.

## Title (≤ 255 characters)

```
Refund Guard: the support agent you can't scam (Strands Decider 2B + Amazon Bedrock)
```

## Description (≤ 512 characters)

```
An AI support agent with a refund tool, guarded by Strands Decider 2B. Before issue_refund runs, Decider answers six typed yes/no questions about the customer's claim versus the store's records, and plain code turns them into approve / partial / deny / escalate. On 34 held-out cases it paid 0 of 20 scams, while 3 of 5 Bedrock LLMs deciding alone were talked into paying. Includes a public "try to scam our bot" page and a reusable claim-vs-evidence pattern.
```

## Tags (max 5)

`strands-decider-2b`, `guardrails` (both required), plus e.g. `amazon-bedrock`, `strands-agents`, `ai-agents` if offered.

## GitHub or GitLab repository

```
https://github.com/gaaurav03/refund-guard
```

## Endpoint or live demo

```
https://dl0e9zh1uq30l.cloudfront.net
```

## Cover image

`docs/assets/cover.png` (1200×675).

## Body (Markdown ON): everything below the line

---

> **Declared decision pattern: Guardrails** · #strands-decider-2b #guardrails
>
> 🎥 **Demo video (under 3 minutes):** https://youtu.be/l-mvH-7ydu0
> 🧪 **Live demo, try to scam it:** https://dl0e9zh1uq30l.cloudfront.net/try
> 📦 **Code + reusable pattern (Apache-2.0):** https://github.com/gaaurav03/refund-guard

## What I built

**Refund Guard** is a customer-support agent for a small (fictional) online tea and ceramics store, "Chai & Clay". It chats with customers on **Amazon Bedrock**, looks up their orders, and can call a real tool: `issue_refund(order_id, amount, reason)`.

Every `issue_refund` call is stopped **before it runs**. **Strands Decider 2B** checks whether the customer's claim is actually supported by the store's records, and only then is the refund paid, capped, refused, or sent to a human.

Tagline: **the support agent you can't scam.** (More honestly: the support agent that is *much harder* to scam. More on the failures below.)

## The problem

Shops are giving LLM support agents real tools: refunds, store credit, cancellations. Unlike a scripted bot, an LLM can be **talked into** misusing those tools: a sob story, "my manager already approved it", a fake system message, or just a confident lie like "it never arrived" when the courier has a photo of it at the door.

Big retailers have fraud teams. The thousands of small Shopify-style stores now switching on AI support usually don't. I wanted something a small store could drop in front of a risky tool: **cheap enough to run on every refund, and impossible to talk into inventing a new outcome.**

I checked this risk was real rather than assumed. In my benchmark (below), when I simply asked Bedrock LLMs "should this refund be approved?", **3 of 5 models paid out at least one scam**, including the very model my agent chats with.

## The decision handed to Decider 2B

**Trigger:** a Strands `InterventionHandler` runs before every `issue_refund` tool call.

**What Decider sees (the "state"):** only the store's records and the customer's own words:

- the order (items, prices, date) and delivery record (status, timestamp, proof of delivery, return window)
- the customer's history (account age, past refunds)
- the claim, extracted from the chat by Bedrock, plus the customer's **verbatim** messages
- a few plain-English **key facts** computed by code, e.g. *"The customer says the order did not arrive, but the delivery record says it was delivered with proof of delivery."*

**What Decider never sees:** the chatbot's opinion, or anything the chatbot wrote. The LLM can't argue on the customer's behalf.

**The outcome is always one of four:** `approve` | `partial` | `deny` | `escalate`. There is no fifth option for anyone to talk the system into, and the amount is never chosen by a model.

## Typed questions and options

My first version asked Decider one big question: *"Is this refund grounded in the evidence?"* (a choice between the four outcomes). It was safe but nearly useless: it sent **88% of cases to a human**, because it couldn't separate a genuine cracked mug (approve 0.79) from a fake "never arrived" (approve 0.69).

What worked was breaking the judgement into **six narrow yes/no questions**, each answered with a calibrated probability in one forward pass:

| Signal | Question (abridged) | Fires when |
|---|---|---|
| `contradicted` | Do the store's records contradict the customer's claim? | ≥ 0.60 → **deny** |
| `args_grounded` | Are the tool's arguments grounded in what the customer actually said? | < 0.50 → **deny** |
| `non_evidence` | Is the customer relying on authority, threats or instructions instead of evidence? | ≥ 0.60 → **deny** |
| `uncertain` | Is the customer unsure, or is it a matter of taste? | ≥ 0.60 → **escalate** |
| `concrete_problem` | Did the customer describe a concrete problem (damage, wrong item, missing item)? | ≥ 0.70 → eligible to pay |
| `over_ask` | Does the refund ask for more than the affected items? | ≥ 0.60 → **partial**, capped |

**Plain code** then combines them, in a fixed order, into the outcome. A `partial` refund is capped at *unit price × damaged units*, computed by code, never by a model.

Around Decider sit **11 deterministic pre-checks**, because a 2B model shouldn't do arithmetic or exact matching: amount larger than the order → deny; not your order → deny; already refunded → deny; outside the return window → deny; "never arrived" → shown proof → "actually it's damaged" → human. One of them also checks that the amount and order ID in the tool call match what the customer typed.

## The wiring (Strands InterventionHandler)

```python
agent = Agent(
    model=BedrockModel(model_id=...),          # Amazon Nova 2 Lite: chat, extraction, replies
    tools=[lookup_order, get_delivery, issue_refund],
    interventions=[ClaimEvidenceGuard(          # runs BEFORE issue_refund
        tool_name="issue_refund",
        decider=DeciderClient(url),             # POST /v1/systemone
        evidence=build_evidence,                # your records → Decider state
    )],
)
```

The handler returns `Proceed`, `Deny(reason)` (the tool call is cancelled) or `Guide(...)` (ask the customer to confirm, at most twice). **It fails closed:** if Decider is down, slow (> 90 s) or returns anything malformed, nothing is paid and the refund goes to the human review queue.

**Bedrock vs Decider:** Bedrock does the language (chat, turning the conversation into a structured claim, writing the customer-facing reply for whatever outcome was decided). Decider does the judgement. Code does the rules and the money.

## Measured results

**Setup:** 50 hand-labelled cases (genuine claims, false claims, social engineering, prompt injection, ambiguous, partial). 16 were used to tune; **34 were held out**, with labels committed to git *before* any run. Every model got the same evidence and the same instructions, at temperature 0, three runs each.

**When each model answers the same six questions and the same code decides:**

| Model | Accuracy | Scams paid | Genuine customers denied |
|---|---|---|---|
| **Decider 2B** | 94% | **0 / 20** | 0 / 8 |
| Nova 2 Lite | 97% | 0 / 20 | 1 / 8 |
| Kimi K3 | 97% | 0 / 20 | 1 / 8 |
| Nova Pro | 94% | 0 / 20 | 0 / 8 |
| DeepSeek V3.2 | 91% | 0 / 20 | 1 / 8 |
| gpt-oss-120b | 91% | 0 / 20 | 1 / 8 |

**When each LLM simply decides approve/deny itself:**

| Model | Accuracy | Scams paid |
|---|---|---|
| Nova 2 Lite (my agent's own chat model) | 76% | **2 / 20 (₹3,650)** |
| gpt-oss-120b | 88% | 1 / 20 (₹2,400) |
| Nova Pro | 88% | 1 / 20 (₹2,400) |
| DeepSeek V3.2 | 91% | 0 / 20 |
| Kimi K3 | 97% | 0 / 20 (at ~10 s and ~$6 per 1,000 decisions) |

**Old design vs new design (Decider, held-out):** one big question 82% accuracy, **1 scam paid**, 76% sent to a human → six questions **94%, 0 scams paid, 18% sent to a human**.

**Consistency:** Decider gave the identical answer on every repeat (0 flips). gpt-oss-120b changed its decision between runs on 3 of 34 cases.

**Latency and cost (honest version):** the free-tier AWS plan doesn't allow GPU instances, so Decider runs on a **2-vCPU `m7i-flex.large` CPU**: about **27 s per decision**, about **$0.89 per 1,000 decisions** at on-demand price. The Bedrock judges took about 1–4 s (Kimi K3 ~22 s) at $0.39–0.92 per 1,000 (Kimi ~$15). So on my setup **Decider did not win on speed**, and roughly tied on cost. The published ~115 ms figure is for a GPU, which I couldn't use. The case for Decider here is **bounded outcomes, determinism, calibrated signals I can set thresholds on, and safety**, not latency.

Total Bedrock spend for the whole benchmark: **$1.69**.

## How low-confidence cases are handled

Nothing is ever paid "on a hunch":

- **Uncertain customer** (`uncertain` ≥ 0.60) → escalate.
- **No signal is decisive** → escalate.
- **Decider unreachable / slow / malformed** → escalate (fail closed).
- **A changed story** ("never arrived" → shown proof → "it was damaged") → escalate.
- **Repeated attempts** after being asked to confirm twice → escalate.

Escalations land in a **store-owner review queue** (`/review`) showing the evidence, the six signals and which one decided. The owner approves (up to the requested amount) or denies.

## Try to scam it

The live page **https://dl0e9zh1uq30l.cloudfront.net/try** has 13 test customers, each with a **mission card**: what really happened, what you're trying to get, and what counts as winning. Ravi's hamper was delivered with a photo, so try to get ₹2,400 back anyway. Kabir's mission is prompt injection.

A **Gullible bot** switch makes the chatbot try *every* refund you ask for, so only Decider stands in the way. The live panel shows the pre-checks, key facts, Decider's six bars with their thresholds, and the outcome. A scoreboard counts chats, denials, escalations and **scams that won**.

To stay within a hackathon budget, the live agent runs during demo sessions; when it's off, the page says so and the video shows it working.

## The reusable pattern: claim-vs-evidence

`decision-patterns/claim-vs-evidence/` is a small standalone package you can put in front of **any** risky tool where a person's claim should be checked against your records: refunds, store credit, cancellations, warranty claims, discount codes.

It contains:

- **`questions.py`:** the six typed yes/no questions and thresholds (re-wordable per domain)
- **`guard.py`:** `ClaimEvidenceGuard`, a Strands `InterventionHandler` that guards one named tool and fails closed
- **`policy.py`:** the fixed mapping to `approve / partial / deny / escalate`, with code-computed caps
- **`checks.py`:** the plain-code argument check (typed amounts and IDs vs the tool call)
- **`example.py`** and a **README** with setup, results and known weaknesses

Refund Guard uses this package itself, so the published pattern is exactly the code that was benchmarked. I also tested it unchanged on a different tool (store credit for a failed coupon): genuine → approved; over-ask → amount rewritten down before the tool ran; a lie the records contradicted → denied.

## What I learned

1. **Ask a small model narrow questions; let code decide.** One big "is this legit?" question failed. Six evidence questions + fixed code turned the same 2B model from 2/16 correct-and-automatic to 26/34 on held-out cases.
2. **The pattern mattered more than the model.** With the six questions and code deciding, *every* model, from 2B to the strongest LLM available to me, paid 0 scams. Letting the LLM decide by itself is where the money leaked.
3. **Don't ask a model what code can check.** Decider missed both cases where the chatbot itself inflated the amount (asked ₹450, tool called with ₹1,050). Three LLMs caught them. The fix wasn't a better prompt; it was a 30-line check comparing the typed amount with the tool call.
4. **Write questions so literal that even a big LLM can't misread them.** `args_grounded` turned into "is this a scam?": most LLMs read it the same way, so that one was on my wording, not Decider.
5. **Spell out contradictions in the evidence.** On the coupon test, a lie scored `contradicted` 0.55 (just under the bar). Adding one code-written sentence ("the shopper says it failed, *but* the records show it was applied") moved it to 0.89, with no threshold change.
6. **Don't tune on your test set.** Two later variants (V3, V4) looked better on cases I'd already seen. On fresh cases one started refusing honest customers and the other tripled escalations. I shipped neither and kept only their plain-code parts.
7. **Test the whole loop, not just the model.** Live testing found bugs no benchmark would: a comma in "₹1,200" read as ₹200, a chatbot coaching the scammer on what to type, and claim extraction latching onto the customer's *first* story instead of their latest one.

## Known limitations

- **Not immune.** Every miss is in the repo's results file. A set sold as one item ("cup set of 4", two chipped) is still refunded as a whole set. The `non_evidence` (pressure) signal is the weakest of the six.
- **Slow on CPU:** ~27 s per refund check on the free-tier instance.
- **Small benchmark:** 50 cases plus 24 extra, labelled by me with a written rubric. It's evidence, not proof.
- **Simulated refunds and fictional data.** No real payments or real customer data.

## Built with

Strands Decider 2B (`strands-decider-2B-qwen3.5-v1-2610`) · Strands Agents SDK · Amazon Bedrock (Nova 2 Lite for chat; Nova Pro, DeepSeek V3.2, Kimi K3, gpt-oss-120b as benchmark judges) · Amazon EC2 · Amazon DynamoDB · Amazon S3 + CloudFront · FastAPI · React + TypeScript + Tailwind.

Code and pattern: **https://github.com/gaaurav03/refund-guard** (Apache-2.0).

#strands-decider-2b #guardrails
