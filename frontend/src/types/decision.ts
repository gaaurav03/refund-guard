// Hand-mirrors backend/app/models.py and the decision record in backend/app/guard/handler.py.
// Field names are canonical (docs/decision.md section 3); do not rename here alone.

export type Outcome = "approve" | "partial" | "deny" | "escalate";
export const OUTCOMES: Outcome[] = ["approve", "partial", "deny", "escalate"];

export type DecidedBy = "precheck" | "decider" | "policy" | "fallback" | "human";

export type SignalName =
  | "args_grounded"
  | "contradicted"
  | "concrete_problem"
  | "non_evidence"
  | "over_ask"
  | "uncertain";

export type Signals = Record<SignalName, number>;

export interface Decision {
  decision_id: string;
  created_at: string;
  order_id: string;
  requested_amount: number;
  outcome: Outcome;
  approved_amount: number;
  decided_by: DecidedBy;
  policy_step: string;
  rule_id: string | null;
  signals: Signals | null;
  key_facts: string[];
  gullible: boolean;
  snippet?: string;
  tries?: number; // public feed: refund tries in this chat
  customer_name?: string; // public feed: demo persona name
  is_scam_success?: boolean;
  decision_latency_ms: number;
  // review queue only
  customer_id?: string;
  status?: string;
}

export interface SignalMeta {
  name: SignalName;
  label: string;
  instructions: string;
  threshold: number;
  fires_when: "above" | "below";
}

export interface Meta {
  signals: SignalMeta[];
  policy_steps: Record<string, string>;
  rules: Record<string, string>;
  max_messages: number;
}

export interface PersonaOrder {
  order_id: string;
  order_date: string;
  items: { name: string; qty: number; unit_price: number }[];
  order_amount: number;
}

export interface Persona {
  customer_id: string;
  name: string;
  label: string;
  orders: PersonaOrder[];
}

export interface SessionInfo {
  session_id: string;
  customer_id: string;
  mode: "chat" | "challenge";
  gullible: boolean;
  max_messages: number;
}

export interface ChatResponse {
  reply: string;
  decisions: Decision[];
  messages_left: number;
}

export interface Scoreboard {
  attempts: number;
  denied: number;
  escalated: number;
  paid_genuine: number;
  scams_succeeded: number;
}

export interface Health {
  ok: boolean;
  decider: { ok: boolean };
  budget_exhausted: boolean;
}
