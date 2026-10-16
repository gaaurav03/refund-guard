# rules.md — Rules for the Coding Agent

> Read this file and [memory.md](memory.md) at the start of every session. When rules conflict, the order of precedence is: security.md > decision.md > this file.

---

## 1. Project structure

```
refund-guard/
├── LICENSE                     # Apache-2.0
├── NOTICE                      # attribution for vendored strands-decider client (Apache-2.0)
├── README.md                   # explicit headings: The decision · Typed question and options · Measured results · Reusable pattern
├── docs/                       # these nine planning docs
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, routes
│   │   ├── config.py           # pydantic-settings, all env vars
│   │   ├── models.py           # RefundClaimState, OrderItem, DeciderResult, Decision (decision.md §3/§5)
│   │   ├── agent/              # Strands agent, system prompt, tools (lookup_order, get_delivery, issue_refund)
│   │   ├── guard/              # prechecks.py, policy.py, state_render.py, decider_client.py, handler.py, ledger.py
│   │   ├── store/              # DynamoDB repositories (rg_* tables)
│   │   └── security/           # rate limiting, session caps, spend counter
│   └── tests/{unit,integration,e2e}/
├── decision-patterns/
│   └── claim-vs-evidence/      # reusable pattern: README.md, verifier.py, questions.py, policy.py, example_discount.py
├── bench/                      # cases.jsonl, LABELING.md, run_bench.py, tune_thresholds.py, report.py, results/
├── frontend/                   # Vite + React + TS + Tailwind; src/{pages,components,api,types}
├── scripts/                    # seed_dynamodb.py, create_tables.py, smoke_*.py
└── infra/                      # systemd units, Caddyfile, IAM policy JSON, deploy.sh
```

## 2. Single source of truth for names

- Use these identifiers exactly: `issue_refund`, `lookup_order`, `get_delivery`, the options `approve | partial | deny | escalate`, every field in decision.md §3, pre-check IDs `PC-01..PC-09`, and tables `rg_*`.
- Python: `backend/app/models.py` (Pydantic v2) is canonical. TS: `frontend/src/types/decision.ts` mirrors it by hand, and a unit test compares the JSON fixtures.
- Option type: `Literal["approve", "partial", "deny", "escalate"]` / `type Outcome = "approve" | "partial" | "deny" | "escalate"`.
- `decided_by`: `precheck | decider | policy | fallback | human`.
- Renaming anything requires updating decision.md first, then the code, then the other docs, all in the same commit.

## 3. Python conventions

- Python 3.11+, `ruff` (lint + format), `mypy --strict` on `app/guard` and `app/models.py`.
- Type hints everywhere; Pydantic models at every boundary (HTTP, DynamoDB, Decider, Bedrock extraction).
- Pure functions for `prechecks`, `policy` and `partial_cap`, with no I/O, so they are trivially unit-tested.
- Thresholds and limits come from `config.py` and are never written as literals elsewhere.
- Use `logging` with JSON formatter, not `print`. Use `decimal`-safe money handling: store INR as integers in paise in DynamoDB and convert at the edges.
- Pin dependencies in `backend/requirements.txt` (`strands-agents`, `strands-decider`, `fastapi`, `boto3`, `pydantic`).

## 4. TypeScript conventions

- `strict: true`, ESLint + Prettier, function components + hooks. Avoid adding a state library unless it's needed.
- All API calls go through `src/api/client.ts` with typed responses, and the UI never parses untyped JSON.
- Tailwind theme tokens come from design.md §1. Do not use hard-coded hex values in components.
- Accessibility: outcome = colour + icon + label; buttons have labels; focus states are visible.

## 5. Never invent external APIs

- Before using any external API (Strands, strands-decider, Bedrock, boto3), check the official docs or the source in the repo. For Decider, `examples/strands/` in `strands-labs/strands-decider` is the reference.
- If something cannot be confirmed, write `# TODO-VERIFY(TV-xx): <what>`, add it to memory.md "Open questions", and isolate it behind one adapter function.
- Do not guess Bedrock model IDs. They come from env vars and are checked in the console.

## 6. Fail closed

- Any exception in the guard path → `escalate`. Never write `except: return Proceed()`.
- `issue_refund` executes only with a matching ledger entry (`approve`/`partial`, amount ≤ `approved_amount`).
- A refund must not execute unless its decision log write succeeded.
- Every new code path that can move money needs a unit test that shows it fails closed.

## 7. Secrets and security

- Never hard-code secrets, account IDs, ARNs with account numbers, or tokens. Use `.env.example` with names only, and add `.env` to `.gitignore`.
- `customer_id` always comes from the session and never from the LLM or the request body of `/api/chat`.
- Do not log raw IPs or full prompts in production.
- Follow the public-demo limits in security.md §4, and do not raise them without updating that file.

## 8. Commits and docs

- Make small commits with a single purpose and imperative messages that use a scope, e.g. `guard: add PC-05 sku check`, `bench: add 10 injection cases`, `docs: sync thresholds`.
- Run `pytest backend/tests/unit` and `npm test` before each commit, and do not commit with failing unit tests.
- Any behaviour change updates the relevant doc (decision.md, security.md, tests.md) in the same commit.
- At the end of each session, append to memory.md's progress log, update status, and remove resolved TODO-VERIFY items.

## 9. AWS cost discipline

- Stop the EC2 instance at the end of every working session (`aws ec2 stop-instances`). Note this in the progress log.
- Use DynamoDB on-demand billing, and do not create provisioned capacity, NAT gateways, load balancers or Elastic IPs left unattached.
- Run benchmarks with Bedrock only on the dev/test splits; never loop on full runs. Estimate the cost before each run.
- Tag every resource `project=refund-guard`, and do not create resources outside `ap-southeast-2` (the SCP blocks other regions anyway).
- Budget alarms at $20/$50 must exist before the instance goes public.
