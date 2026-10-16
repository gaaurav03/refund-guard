import type { Meta } from "../types/decision";

/**
 * Fallback copy of GET /api/meta (backend/app/api.py) so the landing page renders fully even when
 * the live backend is asleep. Live pages always prefer the server's values.
 */
export const STATIC_META: Meta = {
  signals: [
    { name: "args_grounded", label: "Arguments grounded in what the customer said", instructions: "", threshold: 0.5, fires_when: "below" },
    { name: "contradicted", label: "Records contradict the claim", instructions: "", threshold: 0.6, fires_when: "above" },
    { name: "concrete_problem", label: "Concrete problem described", instructions: "", threshold: 0.7, fires_when: "above" },
    { name: "non_evidence", label: "Pressure or instructions instead of evidence", instructions: "", threshold: 0.6, fires_when: "above" },
    { name: "over_ask", label: "Asks for more than the affected items", instructions: "", threshold: 0.6, fires_when: "above" },
    { name: "uncertain", label: "Customer unsure / matter of taste", instructions: "", threshold: 0.6, fires_when: "above" },
  ],
  policy_steps: {
    "decider:args_ungrounded": "Refund arguments don't match what the customer said",
    "decider:contradicted": "Store records contradict the claim",
    "decider:pressure_with_problem": "Real problem, but with pressure: a human checks",
    "decider:non_evidence": "Pressure or instructions instead of evidence",
    "decider:uncertain": "Customer is unsure: a human checks",
    "decider:partial": "Real problem with some items: refund capped to those items",
    "decider:approve": "Concrete problem, nothing contradicts it",
    "policy:no_items_identified": "No item identified: a human checks",
    "policy:no_concrete_problem": "No concrete problem established: a human checks",
  },
  rules: {
    "PC-03": "Amount is zero or larger than the order",
  },
  max_messages: 20,
};
