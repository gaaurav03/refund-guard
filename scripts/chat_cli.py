"""Chat with the Refund Guard agent in the terminal (real Bedrock, real Decider, real DynamoDB).

Usage:
  python scripts/chat_cli.py --customer CUST-007                       # interactive
  python scripts/chat_cli.py --customer CUST-007 --say "msg 1" --say "msg 2"   # scripted
  python scripts/chat_cli.py --memory ...                               # in-memory seed data instead of DynamoDB
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agent.bedrock import make_converse  # noqa: E402
from app.agent.build import build_agent  # noqa: E402
from app.agent.session import Session  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.guard.decider_client import HttpDeciderClient  # noqa: E402
from app.guard.ledger import Ledger  # noqa: E402
from app.store.repo import DynamoRepo, InMemoryRepo  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--customer", required=True)
    ap.add_argument("--say", action="append", default=[])
    ap.add_argument("--model", default=None, help="override BEDROCK_MODEL_ID")
    ap.add_argument("--memory", action="store_true")
    ap.add_argument("--gullible", action="store_true", help="naive chatbot; only the guard stands in the way")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    s = get_settings()
    model_id = args.model or s.bedrock_model_id
    if not model_id:
        sys.exit("Set BEDROCK_MODEL_ID in .env or pass --model")
    repo = InMemoryRepo.seeded() if args.memory else DynamoRepo(region=s.aws_region, prefix=s.ddb_table_prefix)
    agent = build_agent(
        settings=s,
        repo=repo,
        decider=HttpDeciderClient(s.strands_decider_url, s.decider_timeout_ms),
        converse=make_converse(model_id, s.aws_region),
        ledger=Ledger(),
        model_id=model_id,
        gullible=args.gullible,
    )
    session = Session(customer_id=args.customer, gullible=args.gullible)
    mode = "GULLIBLE" if args.gullible else "normal"
    print(f"[session {session.session_id} | customer {args.customer} | model {model_id} | {mode} mode]")

    def turn(text: str) -> None:
        session.add_customer_message(text)
        seen = len(session.decisions)
        t0 = time.perf_counter()
        reply = agent(text, invocation_state={"session": session})
        print(f"\nbot ({(time.perf_counter() - t0):.1f}s): {str(reply).strip()}")
        for d in session.decisions[seen:]:
            probs = {k: round(v, 3) for k, v in (d.get("probs") or {}).items()}
            keys = ("outcome", "approved_amount", "decided_by", "policy_step", "rule_id",
                    "args_grounded_p", "manipulation_p", "decision_latency_ms")
            shown = {k: d[k] for k in keys if d.get(k) is not None} | {"probs": probs}
            print("  [guard] " + json.dumps(shown))

    if args.say:
        for text in args.say:
            print(f"\nyou: {text}")
            turn(text)
        return
    while True:
        try:
            text = input("\nyou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text in {"", "quit", "exit"}:
            break
        turn(text)


if __name__ == "__main__":
    main()
