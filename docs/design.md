# design.md — UI/UX Design

> Three screens: **(1) Customer chat**, **(2) "Try to scam our bot" challenge**, **(3) Store-owner review queue**.
> Outcome values and field names match [decision.md](decision.md).

---

## 1. Visual direction

**Feel:** a calm, trustworthy bank-statement look for the guard, with a little personality for the store (Chai & Clay). It should not look like a purple-gradient AI template.

| Token | Value | Use |
|---|---|---|
| `ink` | `#1B1F23` | text |
| `paper` | `#FAF7F2` | page background (warm off-white) |
| `clay` | `#B5562C` | store brand accent, primary buttons |
| `slate` | `#3C4A57` | guard panel chrome |
| `approve` | `#2E7D4F` | outcome chip, bar |
| `partial` | `#C08A1E` | outcome chip, bar |
| `deny` | `#B3261E` | outcome chip, bar |
| `escalate` | `#3E5BA9` | outcome chip, bar |

- **Type:** "Inter" for UI, "JetBrains Mono" for evidence/probabilities (numbers line up), "Fraunces" for the store wordmark and page headings only.
- Outcome colours are always paired with an icon and a label (✓ approve, ◐ partial, ✕ deny, ↑ escalate), so colour is never the only signal.
- Dark mode: guard panel only (slate background), so it reads as "the machine room".
- Motion: confidence bars animate from 0 → p over 400 ms, and the outcome chip appears after the bars. This is the money shot in the video.

## 2. Screen 1 — Customer chat (`/`)

```
┌──────────────────────────────────────────────┐
│ Chai & Clay · Support            [order ▾]   │
├──────────────────────────────────────────────┤
│  bot: Hi Asha! How can I help?               │
│                     you: my mug arrived      │
│                          cracked             │
│  ┌ Refund decision ───────────────────────┐  │
│  │ ✓ APPROVED  ₹450   · checked in 140 ms │  │
│  │ [why?]                                  │  │
│  └─────────────────────────────────────────┘  │
│  bot: Sorry about that! ₹450 is on its way.  │
├──────────────────────────────────────────────┤
│ [ type a message…                    ] [➤]   │
└──────────────────────────────────────────────┘
```

- Persona banner: the logged-in persona (seeded customer) and an order selector.
- An inline **decision card** appears when `issue_refund` was attempted: outcome chip, amount, latency and a "why?" toggle showing the evidence fields used.
- Escalate card: "Sent to a human reviewer. Usually within 1 business day." Never shown as a failure.

## 3. Screen 2 — "Try to scam our bot" (`/challenge`)

Desktop: a 3-column layout with chat (left 40%), live decision panel (centre 35%) and scoreboard (right 25%).

```
┌ Try to scam our bot ───────────────────────────────────────────────────┐
│ Pick a persona: [Asha · ORD-1042 ₹1,050] [Ravi · ORD-2077 ₹2,400] …    │
├───────────────┬──────────────────────────────┬─────────────────────────┤
│ CHAT          │ LIVE DECISION                │ SCOREBOARD              │
│               │ issue_refund(ORD-2077, 2400) │ Attempts        1,284   │
│ you: it never │ Pre-checks  ✓ 9/9 passed     │ Scams that won     3    │
│ arrived!!     │ Decider 2B   212 ms          │ Denied           801    │
│               │  approve  ▏ 0.03             │ Escalated        480    │
│               │  partial  ▏ 0.02             │ ───────────────         │
│               │  deny     █████████ 0.91     │ Recent:                 │
│               │  escalate ▍ 0.04             │ ✕ "manager said…" 2m    │
│               │ Manipulation ▓▓░░ 0.38       │ ↑ "tastes off"   5m     │
│               │ Evidence used:               │ ✕ "ignore rules" 6m     │
│               │  delivery: delivered ✓ POD   │                         │
│               │  past refunds: 3 (₹6,100)    │                         │
│               │ ┌───────────────┐            │                         │
│               │ │ ✕ DENIED      │ policy: p≥0.85                      │
│               │ └───────────────┘            │                         │
└───────────────┴──────────────────────────────┴─────────────────────────┘
```

- **Panel sections in order:** tool call → pre-checks (which rule fired, if any) → "Args grounded in what you said?" yes/no gauge → Decider bars (4 options, threshold tick mark at 0.85/0.80) → manipulation gauge → evidence used → final outcome + `decided_by` + policy step.
- If a pre-check fires, the Decider section shows "Not needed: PC-03 amount exceeds order" in grey. This shows the cheap rules doing their job.
- **Scoreboard:** `attempts`, `scams_succeeded` (red if > 0, honest), `denied`, `escalated`, plus a recent feed with the first 30 chars of the user's message, sanitised.
- Rules box (collapsible): "Refunds are simulated. No real money. Be creative. Abuse = rate limited."
- **Win state:** if `is_scam_success`, show a "You beat it! 🎉 We logged this for the benchmark" banner. Honesty is part of the pitch.

## 4. Screen 3 — Review queue (`/review`, reviewer token)

| Column | Content |
|---|---|
| Time | relative |
| Customer / order | `CUST-023 · ORD-5150` |
| Claim | `claimed_reason` + first quote |
| Requested | `₹` amount |
| Decider | mini bars + top option |
| Why escalated | `policy_step` text, e.g. "no option ≥ threshold" / "manipulation 0.72" / "Decider timeout" |
| Action | **Approve** (amount editable, ≤ `requested_amount`) · **Deny** · note |

Clicking a row opens a drawer with the full `RefundClaimState`, the transcript and the decision log entry. On resolve, the row animates out and the decision is logged with `decided_by = human`.

## 5. States

| State | Chat | Challenge | Review |
|---|---|---|---|
| Loading | typing dots; decision card skeleton with a "Checking evidence…" shimmer | panel bars at 0 with shimmer | table skeleton rows |
| Error | "Something went wrong, so your request went to a human." (fail closed, never "try again to get refund") | panel shows `fallback → escalate` in escalate colour | toast + retry |
| Empty | greeting + 3 suggested prompts | "Pick a persona and try your best scam" + example attacks | "Queue clear ☕" illustration |
| Rate-limited | "You've hit the message limit for this session." | same + countdown | n/a |
| Demo offline (EC2 stopped / budget cap) | full-page card "Demo sleeping. See the video" with link | same | same |

## 6. Mobile behaviour

- Chat: full width; decision card stays inline.
- Challenge: tabs **Chat | Decision | Score**. A badge on the "Decision" tab pulses when a new decision lands, and tapping it opens the panel.
- Review: rows become cards; the action buttons are sticky at the bottom of the drawer.
- Min tap target 44 px; 16 px side gutter; no horizontal scroll.

## 7. Moments that must look good in the video (< 3 min)

| t | Moment | Screen |
|---|---|---|
| 0:00–0:15 | Hook: "I tried to scam my own support bot" + tagline | challenge |
| 0:15–0:40 | S1 genuine claim → green ✓ APPROVED in ~instant, bars animate | chat |
| 0:40–1:10 | S2 "never arrived" → deny bar fills to 0.9, evidence "POD ✓" highlighted | challenge |
| 1:10–1:35 | S4 injection "ignore your rules… ₹50,000" → "PC-03 blocked, Decider not needed" | challenge |
| 1:35–1:55 | S3 manager claim → manipulation gauge red → escalate; S5 lands in review queue → reviewer resolves | challenge → review |
| 1:55–2:10 | S6 partial → amber chip, capped ₹ amount | chat |
| 2:10–2:40 | Measured results table: Decider vs. LLM-as-judge (latency, cost, attack success) | slide |
| 2:40–2:55 | Reusable pattern folder + "what I learned" + tags | repo / slide |

Recording: 1920×1080, browser zoom 125%, no music or royalty-free only, no third-party logos or brand names. The store is fictional. Judges are not required to watch past 3:00, so the decision must be visible by 0:40. Put "Declared pattern: Guardrails" on screen in the first 15 s.
