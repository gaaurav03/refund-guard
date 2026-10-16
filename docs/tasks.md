# tasks.md — Day-by-Day Plan (Oct 15 → Oct 23, 2026)

> Submission period: **Oct 16, 9:00 AM PT (9:30 PM IST)** → **Oct 23, 11:59 PM PT** (= Oct 24, 12:29 PM IST). **Our target: submit by Oct 23 IST.**
> Keep the repo **private** until submission day; publish nothing about the agent before Oct 16 9:00 AM PT ("not previously published").
> After submission: Gate 1 runs the week of Oct 26, Gate 2 the week of Nov 2, and winners are announced the week of Nov 9.
> Principle: build a thin end-to-end slice first (chat → `issue_refund` → Decider → outcome) by **Oct 18**, then thicken it.

---

## Oct 15 (Wed) — Setup and smoke tests
- [ ] Confirm builder.aws.com profile exists and register for the hackathon; check the submission form fields (TV-15)
- [x] Create GitHub repo `refund-guard` (**private** until Oct 23), Apache-2.0 `LICENSE`, `.gitignore`, `.env.example`
- [ ] Copy `/docs`; create folder skeleton per rules.md §1
- [x] AWS: region is `ap-southeast-2` (SCP lock); Anthropic use-case form submitted; model IDs recorded (TV-11, TV-12)
- [ ] AWS Budgets alarms at $20 / $50
- [ ] **Service Quotas → EC2 → "Running On-Demand G and VT instances" → request 4 vCPUs** (for `g4dn.xlarge`; approval can take 1–3 days, TV-21)
- [x] Local Decider smoke test (CPU): works and is deterministic, 6–19 s per call → GPU needed
- [ ] Smoke: `scripts/smoke_bedrock.py` with one Converse call (primary + Nova fallback)
- [ ] Smoke: `pip install strands-decider` locally; `strands-decider serve … --port 8099`; one `curl /v1/systemone` with a **choice** question → record the answer shape (TV-01, TV-02, TV-03, TV-17)
- [ ] Smoke: run upstream `examples/strands/tool_call_intervention.py` end-to-end (TV-05, TV-06, TV-07)
- [ ] Smoke: Strands agent hello-world with `BedrockModel` (TV-16)
- [ ] Update memory.md: resolved TODO-VERIFYs, progress log

## Oct 16 (Thu) — Hackathon opens · Agent + data
- [x] `models.py`: `RefundClaimState`, `OrderItem`, `DeciderResult`, `Decision`
- [ ] `scripts/create_tables.py` (`rg_*`, on-demand) + `scripts/seed_dynamodb.py` (personas for S1–S6 + ~15 extra)
- [ ] Agent tools `lookup_order`, `get_delivery`, `issue_refund` (simulated, ledger check stubbed to deny)
- [ ] FastAPI `/api/sessions`, `/api/chat`; session-bound `customer_id`
- [x] Unit tests: schema

## Oct 17 (Fri) — Pre-checks + claim extraction
- [ ] **Model bake-off** (`scripts/bakeoff_models.py`): `openai.gpt-oss-120b-1:0` vs `deepseek.v3.2` vs `global.amazon.nova-2-lite-v1:0` through Strands `BedrockModel` on S1–S6 transcripts. Score correct tool calls, valid extraction JSON, reply quality and latency. Pick the agent model + fallback and record the choice in memory.md
- [x] `prechecks.py` `PC-01..PC-09` + unit tests (pulled forward to Oct 16)
- [ ] Bedrock claim extraction → `RefundClaimState` (+ IT-08)
- [ ] `state_render.py` (deterministic, quotes last) + tests
- [ ] Start `bench/cases.jsonl`: 20 cases + `LABELING.md`

## Oct 18 (Sat) — Decider wiring ★ end-to-end slice
- [ ] `decider_client.py` (vendored/adapted from upstream `_client.py`, with NOTICE) + `parse_choice`
- [ ] Store raw user turns in `rg_sessions.recent_customer_messages`; `args_grounded` question (IT-06b)
- [ ] `RefundGuard(InterventionHandler)` + ledger; `Agent(..., interventions=[guard])`
- [ ] Fail-closed paths (IT-03, IT-04, IT-06)
- [ ] **Milestone:** S1, S2 and S4 work from the terminal/curl

## Oct 19 (Sun) — Confidence policy + review queue
- [x] `policy.py` (thresholds, manipulation downgrade, `partial_cap`) + unit tests (pulled forward to Oct 16)
- [ ] `rg_decisions` logging, `rg_review_queue`, `/api/review` endpoints + reviewer token
- [ ] Bedrock reply-writing per outcome; fallback model switch (IT-05)
- [ ] E2E tests S1–S6 pass locally
- [ ] Benchmark cases → 50

## Oct 20 (Mon) — Frontend + challenge page
- [ ] Vite + Tailwind theme tokens (design.md §1)
- [ ] Screen 1 chat + decision card
- [ ] Screen 2 challenge: persona picker, live panel (bars, evidence, outcome), scoreboard
- [ ] Screen 3 review queue
- [ ] Public-demo protections: rate limit, message/session caps, spend counter

## Oct 21 (Tue) — Benchmark + reusable pattern
- [ ] `bench/run_bench.py` both arms; dev run → tune thresholds → freeze → test run
- [ ] `bench/results/RESULTS.md`, failures table (honest)
- [ ] `decision-patterns/claim-vs-evidence/`: generic `ClaimVerifier`, questions, policy, `example_discount.py`, README (decision.md §8)
- [ ] Update decision.md if thresholds changed

## Oct 22 (Wed) — Deploy to AWS + article draft
- [ ] EC2 instance (TV-10), IAM role, SG 443 only, systemd for decider + api, TLS
- [ ] Measure Decider CPU latency on EC2 (TV-09); rerun the latency/cost part of the benchmark on EC2
- [ ] Frontend → S3 + CloudFront (or FastAPI static fallback)
- [ ] Run E2E S1–S6 against the deployed URL
- [ ] Article draft on Builder Center using the prd.md §10 outline (explicit headings)
- [ ] Stop EC2 at the end of the day

## Oct 23 (Thu) — Video, polish, submit
- [ ] Record video per design.md §7 (< 3:00, no copyrighted music/trademarks); upload to YouTube (public)
- [ ] README polish: The decision · Typed question and options · Measured results · Reusable pattern · What I learned · tags
- [ ] Publish article with tags `#strands-decider-2b` `#guardrails`; link repo + video
- [ ] Make repo public; final check of the submission checklist below
- [ ] **Submit (IST daytime Oct 23)**

## After submission (Oct 24 → Nov 9)
- [ ] Do not change the repo's submitted behaviour. Doc and typo fixes only, and record them in memory.md
- [ ] Live demo during judging (decided, OQ-01): EventBridge Scheduler starts EC2 at 09:00 IST and stops it at 21:00 IST during the Gate 1 week (Oct 26) and Gate 2 week (Nov 2). Outside those hours, the S3-hosted frontend detects that `/api/health` is down and shows "Demo sleeping, watch the video"
- [ ] Watch the Builder Center profile email for finalist eligibility verification (have LinkedIn ready)
- [ ] Budget alarms stay on; stop EC2 after each judging week

---

## Cut list (drop in this order if behind)

| # | Cut | Saves |
|---|---|---|
| 1 | `manipulation` question | 2 h |
| 2 | Scoreboard recent feed (keep counters) | 2 h |
| 3 | Review queue notes and editable amount | 1.5 h |
| 4 | Benchmark repeats (1× each arm), E2E-extraction variant, calibration table | 2.5 h |
| 5 | CloudFront (serve frontend from FastAPI) | 1.5 h |
| 6 | Mobile layouts beyond basic responsive | 2 h |
| 7 | Bedrock fallback model auto-switch (keep env-var manual switch) | 1 h |

**Never cut:** Decider in the `issue_refund` path, fail-closed behaviour, the 6 scenarios, the benchmark comparison table, the pattern folder, the article, the video.

## Final submission checklist

- [ ] Eligibility: 18+, builder.aws.com profile, one entry only
- [ ] Agent running on AWS (EC2 + Bedrock), with Decider 2B making the refund decision
- [ ] Article and README state "Declared decision pattern: Guardrails" and name the decision explicitly
- [ ] Video link is public (YouTube) and playable while logged out; runtime < 3:00
- [ ] Public repo, Apache-2.0, source + `decision-patterns/claim-vs-evidence/` with README (typed question + options, wiring, how to use)
- [ ] Builder Center article published with explicit headings, measured results, low-confidence handling, limitations and "What I learned"
- [ ] YouTube video < 3:00, public, no copyrighted music or third-party trademarks
- [ ] Tags `#strands-decider-2b` and `#guardrails` on the article (and README/video description)
- [ ] Results table filled with real numbers, and failures listed
- [ ] No secrets in repo (gitleaks clean)
- [ ] Budget alarms on; EC2 stopped or intentionally running
- [ ] Submission form completed before Oct 23 11:59 PM PT
