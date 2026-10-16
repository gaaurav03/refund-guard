"""Arm B of the benchmark: Bedrock LLM judges on the same 50 cases and the same evidence as Decider 2B.

Two arms per judge (docs/tests.md section 5):
  six     the judge answers the SAME six yes/no questions; the SAME production policy decides
  direct  the judge picks approve | partial | deny | escalate itself (+ confidence); code caps amounts

Usage:
  python bench/run_judges.py --judges B1,B2,B4,B5 --arms six,direct
Results are merged into bench/results/judges.json (resumable: finished rows are skipped).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.guard.policy import Thresholds, apply_policy  # noqa: E402  (production code, imported)
from app.guard.questions import QUESTIONS, SIGNALS  # noqa: E402
from app.guard.state_render import render_state  # noqa: E402
from app.models import DeciderResult, RefundClaimState  # noqa: E402

REGION = "ap-southeast-2"
MAX_TOKENS = 2000  # same budget for every judge; reasoning models need room before the JSON
OUT = ROOT / "bench" / "results" / "judges.json"

JUDGES = {
    "B1": "global.amazon.nova-2-lite-v1:0",  # the agent's own chat model
    "B2": "deepseek.v3.2",
    "B3": "global.moonshotai.kimi-k3",
    "B4": "openai.gpt-oss-120b-1:0",
    "B5": "apac.amazon.nova-pro-v1:0",
}


def load_prompt(name: str) -> tuple[str, str]:
    text = (ROOT / "bench" / "prompts" / f"{name}.md").read_text(encoding="utf-8")
    system = text.split("# SYSTEM", 1)[1].split("# USER", 1)[0].strip()
    user = text.split("# USER", 1)[1].strip()
    return system, user


def first_json(text: str) -> dict[str, Any]:
    text = re.sub(r"<reasoning>.*?</reasoning>", "", text, flags=re.S)
    for m in re.finditer(r"\{[^{}]*\}", text):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    raise ValueError("no JSON object in reply")


def items_value(st: RefundClaimState) -> float | None:
    if not st.claimed_skus:
        return None
    claimed = set(st.claimed_skus)
    return sum(i.unit_price * i.qty for i in st.items if i.sku in claimed)


def decide_six(reply: str, st: RefundClaimState) -> tuple[str, float, str, dict[str, float] | None]:
    try:
        obj = first_json(reply)
        sig = {k: float(obj[k]) for k in SIGNALS}
        if any(not 0.0 <= v <= 1.0 for v in sig.values()):
            raise ValueError("probability out of range")
    except (KeyError, TypeError, ValueError):
        return "escalate", 0.0, "fallback:malformed", None  # fail closed, exactly as for Decider
    d = apply_policy(DeciderResult(signals=sig), st, Thresholds())
    return d.outcome, d.approved_amount, d.policy_step, sig


def decide_direct(reply: str, st: RefundClaimState) -> tuple[str, float, str, dict[str, Any] | None]:
    try:
        obj = first_json(reply)
        option = str(obj["option"]).strip().lower()
        conf = float(obj["confidence"])
        if option not in ("approve", "partial", "deny", "escalate") or not 0.0 <= conf <= 1.0:
            raise ValueError("bad option or confidence")
    except (KeyError, TypeError, ValueError):
        return "escalate", 0.0, "fallback:malformed", None
    raw = {"option": option, "confidence": conf}
    if option in ("approve", "partial"):  # amounts always come from code, as in the production policy
        value = items_value(st)
        if value is None:
            return "escalate", 0.0, "policy:no_items_identified", raw
        capped = round(min(st.requested_amount, value), 2)
        if option == "partial" or capped + 0.01 < st.requested_amount:
            return "partial", capped, "judge:partial", raw
        return "approve", round(st.requested_amount, 2), "judge:approve", raw
    return option, 0.0, f"judge:{option}", raw


def questions_text() -> str:
    return "\n".join(f"- {name}: {q['instructions']}" for name, q in QUESTIONS.items())


def run_one(judge: str, arm: str, cases: list[dict[str, Any]], repeats: int, done: set[tuple[Any, ...]],
            save: Any) -> None:
    client: Any = boto3.client("bedrock-runtime", region_name=REGION,
                               config=Config(read_timeout=120, retries={"max_attempts": 4, "mode": "adaptive"}))
    system, user_tpl = load_prompt(f"judge_{arm}")
    qtext = questions_text()
    for c in cases:
        st = RefundClaimState.model_validate(c["state"])
        evidence = json.dumps(render_state(st), ensure_ascii=False, indent=1)
        user = user_tpl.replace("{evidence}", evidence).replace("{questions}", qtext)
        for rep in range(repeats):
            key = (judge, arm, c["case_id"], rep)
            if key in done:
                continue
            t0 = time.perf_counter()
            err = None
            text, tin, tout = "", 0, 0
            try:
                r = client.converse(
                    modelId=JUDGES[judge],
                    system=[{"text": system}],
                    messages=[{"role": "user", "content": [{"text": user}]}],
                    inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.0},
                )
                text = "".join(b.get("text", "") for b in r["output"]["message"]["content"])
                tin, tout = r["usage"]["inputTokens"], r["usage"]["outputTokens"]
            except Exception as e:  # counted as an error and failed closed
                err = f"{type(e).__name__}: {str(e)[:200]}"
            ms = (time.perf_counter() - t0) * 1000
            outcome, amount, step, raw = (decide_six if arm == "six" else decide_direct)(text, st)
            ok = outcome in c["acceptable_outcomes"] and amount <= c["expected_amount_max"] + 0.01
            save({
                "judge": judge, "model": JUDGES[judge], "arm": arm, "rep": rep, "case_id": c["case_id"],
                "split": c["split"], "category": c["category"], "is_attack": c["is_attack"],
                "expected": c["expected_outcome"], "outcome": outcome, "amount": amount, "step": step,
                "truth_refundable_amount": c["truth_refundable_amount"],
                "args_grounded_label": c.get("args_grounded_label"), "correct": ok, "raw": raw,
                "latency_ms": round(ms, 1), "input_tokens": tin, "output_tokens": tout, "error": err,
                "reply": text[-400:],
            })
            print(f"{judge} {arm:6s} {c['case_id']} r{rep} exp={c['expected_outcome']:8s} got={outcome:8s} "
                  f"{'OK' if ok else 'XX'} {ms/1000:5.1f}s {tin}/{tout}tok{' ERR ' + err if err else ''}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", default="B1,B2,B4,B5")
    ap.add_argument("--arms", default="six,direct")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--split", default="all")
    ap.add_argument("--limit", type=int, default=0, help="only the first N cases (smoke test)")
    args = ap.parse_args()

    lines = (ROOT / "bench" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    cases = [c for c in map(json.loads, lines) if args.split == "all" or c["split"] == args.split]
    if args.limit:
        cases = cases[: args.limit]
    rows: list[dict[str, Any]] = json.loads(OUT.read_text(encoding="utf-8"))["rows"] if OUT.exists() else []
    done = {(r["judge"], r["arm"], r["case_id"], r["rep"]) for r in rows if not r["error"]}
    rows = [r for r in rows if not r["error"]]  # retry errored calls
    lock = threading.Lock()

    def save(row: dict[str, Any]) -> None:
        with lock:
            rows.append(row)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps({"judges": JUDGES, "max_tokens": MAX_TOKENS, "region": REGION,
                                       "rows": rows}, indent=1), encoding="utf-8")

    jobs = [(j, a) for j in args.judges.split(",") for a in args.arms.split(",")]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:  # parallel across judges, sequential within
        futures = [pool.submit(run_one, j, a, cases, args.repeats, done, save) for j, a in jobs]
        for f in futures:
            f.result()
    print(f"\nwrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
