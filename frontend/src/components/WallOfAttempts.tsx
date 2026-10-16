import { useMemo, useState } from "react";
import wall from "../data/wall.json";
import { decidingSignal, inr } from "../lib/decision";
import { STATIC_META } from "../lib/staticMeta";
import type { Outcome, SignalName, Signals } from "../types/decision";
import { OutcomeChip } from "./OutcomeChip";

interface Row {
  id: string;
  category: string;
  message: string;
  requested: number;
  outcome: Outcome;
  paid: number;
  truth: number;
  correct: boolean;
  policy_step: string;
  signals: Signals;
}

const ROWS = wall as Row[];

const CATEGORIES: [string, string][] = [
  ["all", "All"],
  ["false_claim", "False claims"],
  ["social_engineering", "Social engineering"],
  ["prompt_injection", "Prompt injection"],
  ["genuine", "Genuine"],
  ["ambiguous", "Ambiguous"],
  ["partial", "Partial"],
];

const SHORT: Record<SignalName, string> = {
  args_grounded: "args grounded",
  contradicted: "contradicted",
  concrete_problem: "concrete problem",
  non_evidence: "pressure",
  over_ask: "over-ask",
  uncertain: "unsure",
};

/** Razorpay-style browsable table of real held-out benchmark cases and what Decider said. */
export function WallOfAttempts() {
  const [cat, setCat] = useState("all");
  const rows = useMemo(() => ROWS.filter((r) => cat === "all" || r.category === cat), [cat]);
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: ROWS.length };
    ROWS.forEach((r) => (c[r.category] = (c[r.category] ?? 0) + 1));
    return c;
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Filter by category">
        {CATEGORIES.map(([k, label]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={cat === k}
            onClick={() => setCat(k)}
            className={`rounded-full border px-3 py-1 text-[13px] transition-colors ${
              cat === k ? "border-ink bg-ink text-bg" : "border-hairline bg-surface text-muted hover:text-ink"
            }`}
          >
            {label} <span className="font-mono text-[11px] opacity-70">{counts[k] ?? 0}</span>
          </button>
        ))}
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-left">
          <thead className="label">
            <tr className="border-b border-hairline">
              <th className="px-4 py-3 font-normal">What the customer said</th>
              <th className="px-4 py-3 font-normal">Asked</th>
              <th className="px-4 py-3 font-normal">Deciding signal</th>
              <th className="px-4 py-3 font-normal">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const sig = decidingSignal(r.policy_step);
              const value = sig ? r.signals[sig] : null;
              const threshold = STATIC_META.signals.find((s) => s.name === sig)?.threshold;
              return (
                <tr key={r.id} className="border-b border-dashed border-hairline align-top last:border-0">
                  <td className="max-w-[380px] px-4 py-3 text-[13.5px] leading-snug">
                    “{r.message}”
                    <span className="mt-1 block font-mono text-[10.5px] uppercase tracking-wider text-muted">
                      {r.id} · {r.category.replace("_", " ")}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[12.5px]">{inr(r.requested)}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[12px]">
                    {sig && value !== null ? (
                      <>
                        <span className="text-muted">{SHORT[sig]}</span>{" "}
                        <span className="text-accent">{value.toFixed(2)}</span>
                        {threshold !== undefined && <span className="text-muted"> / {threshold}</span>}
                      </>
                    ) : (
                      <span className="text-muted">pre-check</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <OutcomeChip outcome={r.outcome} amount={r.paid} size="sm" />
                    {!r.correct && (
                      <span className="mt-1 block font-mono text-[10.5px] text-deny">
                        ✕ counted as a miss{r.paid > r.truth ? ` (true value ${inr(r.truth)})` : ""}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
