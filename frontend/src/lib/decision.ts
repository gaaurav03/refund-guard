import type { Decision, Meta, Outcome, SignalMeta, SignalName } from "../types/decision";

export const OUTCOME_LABEL: Record<Outcome, string> = {
  approve: "Approved",
  partial: "Partially approved",
  deny: "Denied",
  escalate: "Sent to a human",
};

export const OUTCOME_ICON: Record<Outcome, string> = {
  approve: "✓",
  partial: "◐",
  deny: "✕",
  escalate: "↑",
};

export function inr(n: number): string {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

/** Which Decider signal decided this outcome (mirrors backend/app/guard/policy.py step order). */
export function decidingSignal(policyStep: string): SignalName | null {
  switch (policyStep) {
    case "decider:args_ungrounded":
      return "args_grounded";
    case "decider:contradicted":
      return "contradicted";
    case "decider:pressure_with_problem":
    case "decider:non_evidence":
      return "non_evidence";
    case "decider:uncertain":
      return "uncertain";
    case "decider:partial":
      return "over_ask";
    case "decider:approve":
    case "policy:no_concrete_problem":
    case "policy:no_items_identified":
      return "concrete_problem";
    default:
      return null;
  }
}

/** Does this signal value cross its threshold in the direction that matters? */
export function fires(s: SignalMeta, value: number): boolean {
  return s.fires_when === "below" ? value < s.threshold : value >= s.threshold;
}

/** One plain-language line explaining the outcome. */
export function explain(d: Decision, meta: Meta | null): string {
  if (d.decided_by === "precheck" && d.rule_id) {
    return `${d.rule_id}: ${meta?.rules[d.rule_id] ?? "pre-check rule"}`;
  }
  if (d.decided_by === "fallback") return "Something failed, so it failed closed to a human";
  return meta?.policy_steps[d.policy_step] ?? d.policy_step;
}
