"""Sequential latency of each Bedrock judge (six-question arm), for a fair speed comparison.

The main judge run (run_judges.py) ran all judges in parallel and hit Bedrock throttling, so its
latencies are pessimistic. Here: one judge at a time, one call at a time, 5 warm-up calls discarded,
then the 34 test cases. Wall-clock time of the Converse call, measured client-side from Sydney.

Usage: python bench/latency_judges.py [--judges B1,B2,B3,B4,B5]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_judges import JUDGES, REGION, ROOT, inference_config, load_prompt, questions_text  # noqa: E402

from app.guard.state_render import render_state  # noqa: E402
from app.models import RefundClaimState  # noqa: E402

OUT = ROOT / "bench" / "results" / "latency_judges.json"
WARMUP = 5


def pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(len(s) * q))], 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="B1,B2,B3,B4,B5")
    args = ap.parse_args()
    cases = [c for c in map(json.loads, (ROOT / "bench" / "cases.jsonl").read_text(encoding="utf-8").splitlines())
             if c["split"] == "test"]
    system, tpl = load_prompt("judge_six")
    qtext = questions_text()
    prompts = [tpl.replace("{evidence}", json.dumps(render_state(RefundClaimState.model_validate(c["state"])),
                                                       ensure_ascii=False, indent=1)).replace("{questions}", qtext)
               for c in cases]
    client: Any = boto3.client("bedrock-runtime", region_name=REGION,
                               config=Config(read_timeout=120, retries={"max_attempts": 1}))
    out: dict[str, Any] = {"measured_at": datetime.now(UTC).isoformat(), "region": REGION, "warmup": WARMUP,
                           "n": len(prompts), "judges": {}}
    for j in args.judges.split(","):
        times: list[float] = []
        errors = 0
        for i, user in enumerate(prompts[:WARMUP] + prompts):
            t0 = time.perf_counter()
            try:
                client.converse(modelId=JUDGES[j], system=[{"text": system}],
                                messages=[{"role": "user", "content": [{"text": user}]}],
                                inferenceConfig=inference_config(j))
            except Exception as e:
                errors += 1
                print(f"{j} call {i} ERR {type(e).__name__}", flush=True)
                continue
            ms = (time.perf_counter() - t0) * 1000
            if i >= WARMUP:
                times.append(ms)
        out["judges"][j] = {"model": JUDGES[j], "p50_ms": pct(times, 0.5), "p95_ms": pct(times, 0.95),
                            "mean_ms": round(sum(times) / len(times), 1), "calls": len(times), "errors": errors}
        print(j, out["judges"][j], flush=True)
        OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
