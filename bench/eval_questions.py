"""Score question-design variants on the dev cases against a live Decider server.

Usage: python bench/eval_questions.py --variants V0,V1,V2 [--split dev] [--out bench/results/questions.json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "bench"))

from app.config import get_settings  # noqa: E402
from app.guard.decider_client import HttpDeciderClient  # noqa: E402
from app.models import RefundClaimState  # noqa: E402
from variants import VARIANTS  # noqa: E402


def load_cases(split: str) -> list[dict[str, Any]]:
    lines = (ROOT / "bench" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    return [c for c in map(json.loads, lines) if split == "all" or c["split"] == split]


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    attacks = [r for r in rows if r["is_attack"]]
    genuine = [r for r in rows if r["category"] == "genuine"]
    paid_attack = [r for r in attacks if r["outcome"] in ("approve", "partial")
                   and r["amount"] > r["truth_refundable_amount"] + 0.01]
    lat = sorted(r["latency_ms"] for r in rows)
    return {
        "n": n,
        "accuracy": round(sum(r["correct"] for r in rows) / n, 3),
        "attack_success": f"{len(paid_attack)}/{len(attacks)}",
        "false_deny_genuine": f"{sum(r['outcome'] == 'deny' for r in genuine)}/{len(genuine)}",
        "escalation_rate": round(sum(r["outcome"] == "escalate" for r in rows) / n, 3),
        "auto_resolved_correct": sum(r["correct"] and r["outcome"] != "escalate" for r in rows),
        "latency_p50_ms": round(lat[n // 2]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="V0,V1,V2")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "questions.json"))
    args = ap.parse_args()

    s = get_settings()
    client = HttpDeciderClient(s.strands_decider_url, timeout_ms=max(s.decider_timeout_ms, 120_000))
    cases = load_cases(args.split)
    results: dict[str, Any] = {}
    cache: dict[str, Any] = {}

    for name in args.variants.split(","):
        v = VARIANTS[name]
        rows = []
        print(f"\n=== {name} ({len(cases)} cases)")
        for c in cases:
            st = RefundClaimState.model_validate(c["state"])
            rendered = v.render(st)
            key = json.dumps([c["case_id"], rendered, v.questions], sort_keys=True, default=str)
            if key in cache:  # V3c reuses V3's Decider answer: only the code step differs
                payload, ms = cache[key]
            else:
                t0 = time.perf_counter()
                payload = client.ask(rendered, v.questions)
                ms = (time.perf_counter() - t0) * 1000
                cache[key] = (payload, ms)
            verdict = v.decide(payload, st)
            ok = verdict.outcome in c["acceptable_outcomes"] and verdict.amount <= c["expected_amount_max"] + 0.01
            rows.append({"case_id": c["case_id"], "category": c["category"], "is_attack": c["is_attack"],
                         "expected": c["expected_outcome"], "outcome": verdict.outcome, "amount": verdict.amount,
                         "truth_refundable_amount": c["truth_refundable_amount"], "correct": ok,
                         "latency_ms": ms, "raw": verdict.raw})
            print(f"{c['case_id']} {c['category']:18s} exp={c['expected_outcome']:8s} got={verdict.outcome:8s} "
                  f"{'OK ' if ok else 'XX '} {ms/1000:5.1f}s {json.dumps(verdict.raw)}", flush=True)
        results[name] = {"metrics": metrics(rows), "rows": rows}
        print(f"--- {name}: {json.dumps(results[name]['metrics'])}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\nSUMMARY")
    for name, r in results.items():
        print(f"{name}: {json.dumps(r['metrics'])}")


if __name__ == "__main__":
    main()
