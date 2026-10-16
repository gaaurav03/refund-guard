# design.md — UI/UX Design

> Three screens: **(1) Customer chat**, **(2) "Try to scam our bot" challenge**, **(3) Store-owner review queue**.
> Outcome values and field names match [decision.md](decision.md).

---

## 1. Visual direction: "Claude + terminal accents" (chosen by the user, 2026-10-16)

**Feel:** Claude-like: warm cream background, an editorial serif for headings, one terracotta accent, generous whitespace, hairline borders, no heavy shadows. Calm, text-first and trustworthy. Touches borrowed from developer portfolios: mono uppercase section labels (`01 · THE DECISION`), dashed rules, a blinking cursor in the hero, and a Decider **instrument readout**. Source of truth: `frontend/src/styles/index.css` and `frontend/tailwind.config.js`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | `#F5F1E8` | `#1D1C1A` | page background |
| `surface` | `#FBF9F4` | `#262522` | cards |
| `ink` | `#1F1E1D` | `#ECE8DF` | text |
| `muted` | `#6B665C` | `#A39E93` | secondary text |
| `hairline` | `#E3DCCD` | `#3A3833` | borders, rules |
| `accent` | `#C96442` | `#D97757` | buttons, firing signals, deciding row |
| `approve` / `partial` / `deny` / `escalate` | `#3F7D58` / `#B7862B` / `#B4432F` / `#4A63A8` | lighter variants | outcome chips |

- **Type:** "Newsreader" (serif) for headings, "Inter" for UI, "JetBrains Mono" for labels, numbers and the readout.
- **Themes:** light and dark via CSS variables. The page follows the system setting before first paint, and a toggle saves the choice in localStorage (try/catch).
- Outcome colours are always paired with an icon and a label (✓ approve, ◐ partial, ✕ deny, ↑ escalate).
- **Signal readout:** each of the six signals gets a bar, a threshold tick and a value. Values past their threshold turn accent-coloured. The signal that decided is highlighted with ▸. Bars animate 0 → p over 400 ms (disabled under reduced motion). This is the money shot in the video.
- **Routes:** `/` landing (01 problem · 02 the decision · 03 how it works · 04 measured results · 05 reusable pattern), `/try` challenge (also the store chat: Normal bot / Gullible bot switch), `/review` queue. `/chat` redirects to `/try` (merged on Oct 16: the two pages duplicated each other). Since Oct 17 `/try` shows a **mission card** per demo customer (what really happened, the mission, the win condition, difficulty, starter lines; `frontend/src/lib/missions.ts`). The card is visitor-only: the chatbot and the guard never see it, and the win condition matches the server's `truth_refundable_amount`. Sections 2–4 below describe the app screens. The layouts are implemented in `frontend/src/pages/`.

## 2. Screen 1 — Customer chat (now the Normal-bot mode of `/try`)

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
│               │  args grounded ███████ 0.69  │ Escalated        480    │
│               │  contradicted  ████████ 0.73 │ ───────────────         │
│               │  concrete prob ███ 0.30      │ Recent:                 │
│               │  pressure      ██ 0.28       │ ✕ "manager said…" 2m    │
│               │  over-ask ▏0.18 unsure ▏0.13 │ ↑ "tastes off"   5m     │
│               │ Evidence used:               │ ✕ "ignore rules" 6m     │
│               │  delivery: delivered ✓ POD   │                         │
│               │  past refunds: 3 (₹6,100)    │                         │
│               │ ┌───────────────┐            │                         │
│               │ │ ✕ DENIED      │ step 2: contradicted ≥ 0.60         │
│               │ └───────────────┘            │                         │
└───────────────┴──────────────────────────────┴─────────────────────────┘
```

- **Panel sections in order:** tool call → pre-checks (which rule fired, if any) → KEY FACTS → Decider's six signal bars (each with its threshold tick; the bar that decided is highlighted) → evidence used → final outcome + `decided_by` + the policy step in plain words (e.g. "Records contradict the claim").
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
| Why escalated | `policy_step` text, e.g. "customer unsure (0.73)" / "pressure but a real problem" / "no concrete problem" / "Decider timeout" |
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
| 1:35–1:55 | S3 manager claim (gullible mode) → args-grounded bar low → deny; S5 lands in review queue → reviewer resolves | challenge → review |
| 1:55–2:10 | S6 partial → amber chip, capped ₹ amount | chat |
| 2:10–2:40 | Measured results table: Decider vs. LLM-as-judge (latency, cost, attack success) | slide |
| 2:40–2:55 | Reusable pattern folder + "what I learned" + tags | repo / slide |

Recording: 1920×1080, browser zoom 125%, no music or royalty-free only, no third-party logos or brand names. The store is fictional. Judges are not required to watch past 3:00, so the decision must be visible by 0:40. Put "Declared pattern: Guardrails" on screen in the first 15 s.
