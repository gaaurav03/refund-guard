import { OUTCOME_ICON, OUTCOME_LABEL, inr } from "../lib/decision";
import type { Outcome } from "../types/decision";

const TONE: Record<Outcome, string> = {
  approve: "text-approve border-approve/40 bg-approve/10",
  partial: "text-partial border-partial/40 bg-partial/10",
  deny: "text-deny border-deny/40 bg-deny/10",
  escalate: "text-escalate border-escalate/40 bg-escalate/10",
};

export function OutcomeChip({ outcome, amount, size = "md" }: { outcome: Outcome; amount?: number; size?: "sm" | "md" }) {
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-mono uppercase tracking-wider ${pad} ${TONE[outcome]}`}
      data-testid={`outcome-${outcome}`}
    >
      <span aria-hidden>{OUTCOME_ICON[outcome]}</span>
      {OUTCOME_LABEL[outcome]}
      {amount !== undefined && amount > 0 && <span className="normal-case tracking-normal">· {inr(amount)}</span>}
    </span>
  );
}
