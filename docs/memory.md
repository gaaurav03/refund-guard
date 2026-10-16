# memory.md — Project Memory (read first, append last)

## Summary
**Refund Guard** ("The support agent you can't scam") is our entry for the AWS Strands Decider Agent Hackathon, due **Oct 23, 2026 11:59 PM PT**, with submission planned for Oct 23 IST. It is a Bedrock-powered support agent for a fictional store, Chai & Clay, prices in INR. Every `issue_refund(order_id, amount, reason)` call is intercepted by a Strands `InterventionHandler`. Deterministic pre-checks `PC-01..09` run first, then **Strands Decider 2B** answers "is this refund request grounded in the evidence?" with `approve | partial | deny | escalate`. In the same call, Decider also checks `args_grounded`: are the tool's arguments supported by what the customer actually said? A confidence policy (0.85 / 0.85 / 0.80, else escalate) turns that into an action, and uncertain cases go to a human review queue. The project also includes a public "Try to scam our bot" page, a benchmark of 50 cases comparing Decider with a Bedrock LLM-as-judge, and a reusable pattern in `decision-patterns/claim-vs-evidence/`.

## Current status
- **Phase:** planning docs written and reconciled with the official T&C (Oct 15). No code yet.
- **Accounts:** Builder Center profile registered ✅. New AWS account with **$100 credits** ✅. Budget ceiling = $100 (credits), target < $50.
- **Next:** Oct 15 smoke tests (tasks.md).

## Key decisions
See [decision.md §9 ADRs](decision.md#9-adrs-key-decisions). Short list:
- ADR-01 Decider decides, Bedrock never does · ADR-03 thresholds · ADR-04 tool-side ledger · ADR-06 amounts computed by code · ADR-09 fail closed → `escalate`.

## Naming conventions
- Tools: `lookup_order`, `get_delivery`, `issue_refund`. Options: `approve | partial | deny | escalate`.
- State fields: decision.md §3. `decided_by`: `precheck | decider | policy | fallback | human`.
- Tables `rg_*`; env vars per architecture.md §6; pre-checks `PC-01..PC-09`; tests `IT-xx`, `test_sN_*`; bench cases `B-xxx`; open questions `TV-xx`.

## Known gotchas
- The free plan may restrict instance types and Anthropic models, so Amazon Nova is the fallback. Submit the Anthropic use-case form on day 1.
- **Decider is too slow on CPU for a live demo** (6–19 s per decision locally; the 115 ms figure is GPU). On CPU it runs fp32 and uses about 7 GB RAM. Use a GPU EC2 instance for the demo and benchmark, and keep the decision state compact. Structured JSON state gave more confident answers than prose (approve 0.78 vs 0.45).
- Local smoke test: S1 (genuine cracked mug) scored approve 0.78. That's below 0.85, so it would escalate. Thresholds must be tuned on the dev split.
- Decider's hard-tier accuracy is about 50%, which makes escalation a core feature.
- The upstream example shows only `Proceed`/`Guide`, with no confirmed hard-cancel. The ledger check in `issue_refund` is mandatory.
- The README's serve example uses port 8000, while the example client defaults to 8099 via `STRANDS_DECIDER_URL`. We use 8099.
- **Stop EC2 at the end of every session.** The budget ceiling is $100 and the target is under $50.
- Never say "immune". Say "much harder to manipulate".
- **Local disk: C: is nearly full (≈36 GB free). Everything goes on D:.** The user-level env vars `PIP_CACHE_DIR`, `HF_HOME`, `TORCH_HOME`, `npm_config_cache`, `UV_CACHE_DIR` and `XDG_CACHE_HOME` all point to `D:\devcache\*` (set 2026-10-15). The venv lives at `D:\Desktop\RefendGuardAgent\.venv`. For big installs, also set `TMP`/`TEMP=D:\devcache\tmp` for that command only. The AWS CLI is installed into the venv with pip, not with the MSI that would install to `C:\Program Files`. Run it as `.venv\Scripts\python.exe -m awscli` (`aws.cmd` picks up the global Python).
- **Do NOT delete the local Decider model** in `D:\devcache\huggingface` (4.5 GB), at the user's request (2026-10-16). It is independent of `.venv`, so deleting or recreating the venv keeps it.

## AWS account facts (verified 2026-10-16 via CLI, user `refund-guard-dev`)
- The account is a member of AWS Organization `<org-id>` (management account <org-management-account>). The org's **SCP allows EC2/DynamoDB/Lambda/etc. only in `ap-southeast-2` (Sydney)**, and also blocks SSM, ECS, ECR, SageMaker, Amplify, Scheduler and AgentCore in other regions. S3, CloudFront, IAM, Logs, Cost Explorer and Bedrock work. **All infrastructure goes in ap-southeast-2.** Note: some `describe-*` calls are blocked outside Sydney.
- EC2 dry-run in Sydney: `t3.*`, `c7i.2xlarge`, `g4dn.xlarge`, `g5.xlarge` and `g6.xlarge` are all permitted by the SCP. The G-instance vCPU quota is 0, and request case <case-id> (4 vCPUs) is open.
- Bedrock: **Nova works** (`apac.amazon.nova-lite-v1:0` ~0.8 s, `global.amazon.nova-2-lite-v1:0` ~1.1 s; `apac.amazon.nova-pro-v1:0` is listed). **Claude Haiku 5.5 / Sonnet 5.5:** use-case form on file, `authorizationStatus=AUTHORIZED`, but `agreementAvailability=NOT_AVAILABLE` → invoke fails with "not available for this account". A Marketplace offer exists (`list-foundation-model-agreement-offers`); accepting it is the user's decision (TV-22).
- Bedrock models in Sydney (test-invoked 2026-10-16). **Work (no agreement needed):** `openai.gpt-oss-120b-1:0` 0.8 s, `deepseek.v3.2` 0.7 s, `zai.glm-5` 0.6 s, `global.moonshotai.kimi-k3` 2.2 s, `qwen.qwen3-235b-a22b-2507-v1:0` 2.4 s, `mistral.mistral-large-3-675b-instruct` 7.8 s, `apac.amazon.nova-pro-v1:0` 0.8 s, `global.amazon.nova-2-lite-v1:0` 1.1 s. **Blocked ("not available for this account", Marketplace agreement):** all Claude, `openai.gpt-5.x/6.x`, `zai.glm-5.3`, `xai.grok-*`.
- Budgets: one budget, "My Zero-Spend Budget" ($100 limit), with alerts set up by the user.

## Open questions
| ID | TODO-VERIFY | Where used | Resolve by |
|---|---|---|---|
| — | **Resolved 2026-10-15 (local smoke test, strands-decider 0.1.0, strands-agents 1.61.0):** TV-01 both checkpoints exist, we use `qwen3.5-v1-2610` · TV-02 server default 8000, we pass `--port 8099` · TV-03 choice answer = `{choice, probabilities{}, confidence}` · TV-04 noul = `{"type":"noul","noul":p}` ✔ · TV-05 `strands.interventions` present in 1.61.0 · TV-06 **`Deny(reason)` hard-cancels**; `on_error="deny"` gives fail-closed · TV-07 `event.tool_use["toolUseId"]`, `event.invocation_state` · TV-08 no client in the package, so we vendor one · TV-14 `max_length` 4096 tokens · TV-17 `--device cpu` · TV-18 deterministic (5/5 identical) | | |
| TV-01 | Decider checkpoint name: brief says `strands-decider-2B-hobson-v21`; README (2026-10-15) says `StrandsAgents/strands-decider-2B-qwen3.5-v1-2610` | architecture §6, ADR-11 | Oct 15 |
| TV-02 | Serve port default (README 8000 vs client 8099) | ADR-10 | Oct 15 |
| TV-03 | Exact JSON shape of a `choice` answer (selected option + per-option probabilities field names) | decision §2, `parse_choice` | Oct 15 |
| TV-04 | `noul` answer shape confirmed as `{"type":"noul","noul":<p>}` from the README example only. Verify on a live server | decision §2 | Oct 15 |
| TV-05 | `strands.interventions` (`InterventionHandler`, `Proceed`, `Guide`) available in released `strands-agents` on PyPI; minimum version to pin | decision §7 | Oct 15 |
| TV-06 | Whether an intervention action exists that hard-cancels/denies a tool call (beyond `Guide`) | decision §7, ADR-04 | Oct 15 |
| TV-07 | Key for the tool-use id in `event.tool_use` (e.g. `toolUseId`) and how to access session context in the handler | decision §7, ledger | Oct 15 |
| TV-08 | Whether the Decider client is importable from the pip package or must be vendored from `examples/strands/_client.py` (NOTICE file) | rules §1 | Oct 15 |
| TV-09 | Decider latency on the chosen **GPU** EC2 type. Local CPU measured on i5-12500H (12 cores, fp32): **~20 ms per input token**. 270 tokens = 5.8 s, 608 tokens = 12.3 s, 783 tokens with 3 questions = 19.4 s. That rules out CPU for the live demo (see TV-21) | architecture §7 | Oct 17 |
| TV-22 | ~~Claude or Nova?~~ **Decided 2026-10-16:** no Marketplace models. The agent model is chosen by an Oct 17 bake-off between `openai.gpt-oss-120b-1:0`, `deepseek.v3.2` and `global.amazon.nova-2-lite-v1:0` (tool calling + extraction on S1–S6). The benchmark uses a judge panel (tests.md §5) | — | done |
| TV-21 | **GPU instance access:** a new account's "Running On-Demand G and VT instances" vCPU quota (likely 0) → request 4 vCPUs for `g4dn.xlarge`. Also check whether the free plan allows GPU instances at all, and the hourly price | architecture §5 | **request Oct 15** |
| TV-10 | EC2 instance types allowed on the free plan; `g4dn.xlarge` (and fallbacks) hourly on-demand + spot price | architecture §5 | Oct 15 |
| TV-11 | Anthropic model access on the free plan, exact Bedrock model/inference-profile IDs, required IAM actions | architecture §6, security §5 | Oct 15 |
| TV-12 | Amazon Nova fallback model/inference-profile ID | architecture §6 | Oct 15 |
| TV-13 | Bedrock on-demand token prices for the chosen models (cost metric, spend cap) | tests §6, security §4 | Oct 21 |
| TV-14 | Decider context window (from `/health`) → max state length | decision §3 | Oct 16 |
| TV-15 | *Partly resolved (see below).* Still open: where the tags are entered (article vs. submission form) and the exact submission form fields | tasks Oct 22–23 | Oct 16 |
| TV-16 | Strands `BedrockModel` constructor params (`model_id`, region) and how to switch to the fallback model at runtime | FR-01 | Oct 15 |
| TV-17 | CPU device flag/extra for `strands-decider serve` (`--device cpu`, `[cpu]` extra) | tests §7 | Oct 15 |
| TV-18 | Whether Decider output is deterministic for identical input (benchmark repeats) | tests §5 | Oct 18 |
| TV-19 | S3 + CloudFront (or Amplify) availability on the free plan | architecture §5 | Oct 22 |
| TV-20 | Whether the $100 credits cover Bedrock usage of Anthropic models (Billing → Credits → eligible services). If not, Nova becomes the primary model | architecture §6 | Oct 15 |

### Other open questions (decisions, not verifications)
| ID | Question | Default if undecided | Decide by |
|---|---|---|---|
| OQ-01 | ~~Keep the live demo up during judging?~~ **Decided 2026-10-15:** EC2 runs only during IST daytime (scheduled start/stop); otherwise the frontend shows "Demo sleeping, watch the video" | — | done |

### Resolved from official Terms & Conditions (pasted 2026-10-15, T&C last updated Oct 9, 2026)
| Item | Answer | Impact |
|---|---|---|
| Submission window | Oct 16 9:00 AM PT → Oct 23 11:59 PM PT | Matches plan; nothing public before Oct 16 9:00 AM PT |
| Must the agent be hosted on AWS? | Yes: "build a working agent on AWS" | EC2 hosting is mandatory, not optional; keep the plan |
| Required parts (pass/fail) | Article on Builder Center + public repo (source + labelled pattern) + video; agent must use Decider | prd.md §10 |
| Pattern declaration / tags | `#strands-decider-2b` + exactly **one** pattern tag | `#guardrails` only (ADR-13) |
| Official Guardrails definition | "Before a tool call, verify the arguments are grounded in what the user actually said" | Added `args_grounded` Q0 (ADR-12) |
| License | Any OSI-approved | Apache-2.0 fine |
| Video | < 3:00 (judges needn't watch beyond), public on YouTube/Vimeo/Facebook Video/Youku, no third-party trademarks or copyrighted music | design.md §7 |
| Latency/cost/accuracy/low-confidence reporting | Encouraged, not required; counts as bonus under "Effective use" (30%) | Keep; lower cut priority than mandatory parts |
| Confidence | AWS describes it as "calibrated" | We measure calibration (tests.md §6) |
| Eligibility | 18+, builder.aws.com profile, one entry; India not excluded; finalists may be verified via LinkedIn | tasks.md checklist |
| Free Tier | Free Tier terms apply; account won't be charged without consent | Instance-type limits still TV-10 |
| Judging timeline | Gate 1 week of Oct 26, Gate 2 week of Nov 2, winners week of Nov 9 | OQ-01 |
| Extra recognition | Possible "most-reused / best decision pattern" mention | Invest in the pattern README quality |

## Progress log
<!-- Append one entry per session: date (IST) · what changed · TV items resolved · EC2 stopped? -->
- **2026-10-15:** Wrote the nine planning docs in `/docs`. Checked the strands-decider repo: confirmed `/v1/systemone` request format (`state`, `questions{type,instructions,criteria}`), question types `choice`/`noul`/`score`, `strands.interventions` `InterventionHandler.before_tool_call`, `Proceed()`, `Guide(feedback=)`, and `Agent(interventions=[...])`. No AWS resources were created. EC2: n/a.
- **2026-10-15 (later):** Reconciled the docs with the official About page and T&C. Added `args_grounded` (Q0, verbatim customer messages; ADR-12/13), new state fields `tool_reason` and `recent_customer_messages`, a calibration metric, the eligibility/publishing checklist, a post-submission plan, and OQ-01. TV-15 partly resolved.
- **2026-10-15 (evening):** Set up a venv on D: (caches → `D:\devcache`). Installed strands-decider 0.1.0, strands-agents 1.61.0 and awscli 1.46.1. Read the interventions source (Deny exists) and the Decider schema. Ran Decider locally on CPU: works and is deterministic, but takes 6–19 s per call → plan moved to a GPU EC2 instance (TV-21). Fixtures are in `scripts/out/`. The local server was stopped. EC2: none yet.
