"""Export the held-out benchmark results for the landing page's "Wall of attempts".

Reads bench/cases.jsonl + bench/results/questions_test.json (real Decider answers) and re-runs the
production policy to get the exact deciding step. Writes frontend/src/data/wall.json.
Usage: python scripts/export_wall.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.guard.policy import Thresholds, apply_policy  # noqa: E402
from app.models import DeciderResult, RefundClaimState  # noqa: E402


def main() -> None:
    cases = {c["case_id"]: c for c in map(json.loads, (ROOT / "bench" / "cases.jsonl").read_text("utf-8").splitlines())}
    results = json.loads((ROOT / "bench" / "results" / "questions_test.json").read_text("utf-8"))
    rows = []
    for r in results["V2"]["rows"]:
        c = cases[r["case_id"]]
        state = RefundClaimState.model_validate(c["state"])
        d = apply_policy(DeciderResult(signals=r["raw"]), state, Thresholds())
        rows.append({
            "id": c["case_id"],
            "category": c["category"],
            "message": " ".join(t["text"] for t in c["transcript"]),
            "requested": state.requested_amount,
            "outcome": d.outcome,
            "paid": d.approved_amount,
            "truth": c["truth_refundable_amount"],
            "correct": r["correct"],
            "policy_step": d.policy_step,
            "signals": r["raw"],
        })
    out = ROOT / "frontend" / "src" / "data" / "wall.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
