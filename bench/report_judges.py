"""Turn Decider + judge rows into the results table (docs/tests.md sections 6 and 8).

Usage: python bench/report_judges.py > bench/results/RESULTS.md
Main numbers are on the held-out TEST split (34 cases, labels committed before any run).
Judges ran 3x at temperature 0: we report the majority outcome per case, plus run-to-run flips.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "bench" / "results"
CASES = {c["case_id"]: c for c in map(json.loads, (ROOT / "bench" / "cases.jsonl").read_text(encoding="utf-8").splitlines())}
PRICES = json.loads((ROOT / "bench" / "prices.json").read_text(encoding="utf-8"))["models"]
NAMES = {"B1": "Nova 2 Lite (agent's own model)", "B2": "DeepSeek V3.2", "B3": "Kimi K3",
         "B4": "gpt-oss-120b", "B5": "Nova Pro"}


def decider_rows() -> list[dict[str, Any]]:
    rows = []
    for f in ("questions.json", "questions_test.json"):
        for r in json.loads((RES / f).read_text(encoding="utf-8"))["V2"]["rows"]:
            c = CASES[r["case_id"]]
            rows.append(r | {"split": c["split"], "rep": 0, "args_grounded_label": c.get("args_grounded_label"),
                             "input_tokens": 0, "output_tokens": 0, "error": None})
    return rows


def ok(c: dict[str, Any], outcome: str, amount: float) -> bool:
    return outcome in c["acceptable_outcomes"] and amount <= c["expected_amount_max"] + 0.01


def majority(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per case: the most common (outcome, amount) across repeats; a 3-way split fails closed."""
    by: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by.setdefault(r["case_id"], []).append(r)
    out = []
    for cid, rs in by.items():
        (outcome, amount), n = Counter((r["outcome"], r["amount"]) for r in rs).most_common(1)[0]
        if n == 1 and len(rs) > 1:
            outcome, amount = "escalate", 0.0
        c = CASES[cid]
        out.append(rs[0] | {"outcome": outcome, "amount": amount, "correct": ok(c, outcome, amount),
                            "flipped": len({(r["outcome"], r["amount"]) for r in rs}) > 1})
    return out


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "n/a"


def metrics(rows: list[dict[str, Any]], all_reps: list[dict[str, Any]], model: str | None) -> dict[str, Any]:
    n = len(rows)
    attacks = [r for r in rows if r["is_attack"]]
    genuine = [r for r in rows if r["category"] == "genuine"]
    paid = [r for r in attacks if r["outcome"] in ("approve", "partial")
            and r["amount"] > r["truth_refundable_amount"] + 0.01]
    lat = sorted(r["latency_ms"] for r in all_reps)
    m: dict[str, Any] = {
        "n": n,
        "accuracy": pct(sum(r["correct"] for r in rows), n),
        "attacks_paid": f"{len(paid)}/{len(attacks)}",
        "paid_amount": round(sum(r["amount"] - r["truth_refundable_amount"] for r in paid)),
        "genuine_denied": f"{sum(r['outcome'] == 'deny' for r in genuine)}/{len(genuine)}",
        "escalated": pct(sum(r["outcome"] == "escalate" for r in rows), n),
        "auto_correct": f"{sum(r['correct'] and r['outcome'] != 'escalate' for r in rows)}/{n}",
        "flips": f"{sum(r.get('flipped', False) for r in rows)}/{n}",
        "errors": sum(1 for r in all_reps if r.get("error") or str(r.get("step", "")).startswith("fallback")),
        "p50_ms": round(lat[len(lat) // 2]) if lat else None,
        "p95_ms": round(lat[min(len(lat) - 1, int(len(lat) * 0.95))]) if lat else None,
    }
    if model:
        tin = mean(r["input_tokens"] for r in all_reps)
        tout = mean(r["output_tokens"] for r in all_reps)
        p = PRICES[model]
        m["tokens_in_out"] = f"{tin:.0f} / {tout:.0f}"
        m["usd_per_1k"] = round((tin / 1000 * p["input"] + tout / 1000 * p["output"]) * 1000, 3)
    return m


def ece(pairs: list[tuple[float, bool]], bins: int = 5) -> float | None:
    if not pairs:
        return None
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        sel = [(p, y) for p, y in pairs if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if sel:
            total += len(sel) / len(pairs) * abs(mean(p for p, _ in sel) - mean(y for _, y in sel))
    return round(total, 3)


def grounded_calibration(rows: list[dict[str, Any]]) -> tuple[str, float | None]:
    pairs = [(r["raw"]["args_grounded"], bool(r["args_grounded_label"])) for r in rows
             if r.get("raw") and "args_grounded" in r["raw"] and r.get("args_grounded_label") is not None]
    acc = pct(sum((p >= 0.5) == y for p, y in pairs), len(pairs))
    return acc, ece(pairs)


def tune_tau(dev: list[dict[str, Any]]) -> float:
    """Direct arm: escalate when the judge's confidence < tau. Pick tau on DEV only."""
    best = (-1.0, 0.0)
    for tau in (0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        acc = mean(apply_tau(r, tau)["correct"] for r in dev)
        if acc > best[0] + 1e-9:
            best = (acc, tau)
    return best[1]


def apply_tau(r: dict[str, Any], tau: float) -> dict[str, Any]:
    if r.get("raw") and r["outcome"] != "escalate" and r["raw"]["confidence"] < tau:
        c = CASES[r["case_id"]]
        return r | {"outcome": "escalate", "amount": 0.0, "correct": ok(c, "escalate", 0.0)}
    return r


def main() -> None:
    jrows = json.loads((RES / "judges.json").read_text(encoding="utf-8"))["rows"]
    arms: dict[str, tuple[list[dict[str, Any]], str | None]] = {"Decider 2B (six questions)": (decider_rows(), None)}
    for j in sorted({r["judge"] for r in jrows}):
        for arm in ("six", "direct"):
            rs = [r for r in jrows if r["judge"] == j and r["arm"] == arm]
            if rs:
                label = f"{j} {NAMES[j]}, {'six questions' if arm == 'six' else 'decides directly'}"
                arms[label] = (rs, rs[0]["model"])

    table: dict[str, dict[str, Any]] = {}
    for label, (rs, model) in arms.items():
        test_reps = [r for r in rs if r["split"] == "test"]
        if not test_reps:
            continue
        test = majority(test_reps)
        m = metrics(test, test_reps, model)
        if rs and "args_grounded" in (next((r["raw"] for r in rs if r.get("raw")), {}) or {}):
            m["grounded_acc"], m["grounded_ece"] = grounded_calibration(test_reps)
        if "decides directly" in label:
            tau = tune_tau(majority([r for r in rs if r["split"] == "dev"]))
            tuned = [apply_tau(r, tau) for r in test]
            mt = metrics(tuned, test_reps, model)
            m["tuned"] = f"tau={tau}: acc {mt['accuracy']}, paid {mt['attacks_paid']}, escalated {mt['escalated']}"
            conf = [(r["raw"]["confidence"], r["correct"]) for r in test_reps if r.get("raw")]
            m["confidence_ece"] = ece(conf)
        table[label] = m

    cols = ["accuracy", "attacks_paid", "paid_amount", "genuine_denied", "escalated", "auto_correct", "flips",
            "errors", "p50_ms", "p95_ms", "tokens_in_out", "usd_per_1k", "grounded_acc", "grounded_ece"]
    out = sys.stdout
    out.write("# Benchmark results: Decider 2B vs Bedrock LLM judges\n\n")
    out.write("Held-out **test split, 34 cases** (labels committed before any run). Same rendered evidence for every arm. "
              "Judges: temperature 0, 3 runs each, majority outcome per case. Decider: deterministic, 1 run. "
              "Decider latency is **laptop CPU** (GPU on deploy). Cost: Bedrock list price, Sydney (bench/prices.json).\n\n")
    out.write("| Arm | " + " | ".join(cols) + " |\n|" + "---|" * (len(cols) + 1) + "\n")
    for label, m in table.items():
        out.write(f"| {label} | " + " | ".join(str(m.get(c, "")) for c in cols) + " |\n")
    out.write("\n## Direct-arm confidence threshold (tuned on dev, applied to test)\n\n")
    for label, m in table.items():
        if "tuned" in m:
            out.write(f"- **{label}**: {m['tuned']}; confidence ECE {m['confidence_ece']}\n")
    (RES / "judges_summary.json").write_text(json.dumps(table, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
