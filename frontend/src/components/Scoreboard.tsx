import { OutcomeChip } from "./OutcomeChip";
import type { Decision, Scoreboard as Score } from "../types/decision";

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-dashed border-hairline py-2 last:border-0">
      <span className="text-sm text-muted">{label}</span>
      <span className={`font-mono text-lg tabular-nums ${tone ?? ""}`}>{value}</span>
    </div>
  );
}

export function Scoreboard({ score }: { score: Score | null }) {
  const s = score ?? { attempts: 0, denied: 0, escalated: 0, paid_genuine: 0, scams_succeeded: 0 };
  return (
    <div data-testid="scoreboard">
      <Stat label="Chats that tried a refund" value={s.attempts} />
      <Stat label="Denied" value={s.denied} />
      <Stat label="Sent to a human" value={s.escalated} />
      <Stat label="Paid (genuine)" value={s.paid_genuine} />
      <Stat label="Scams that won" value={s.scams_succeeded} tone={s.scams_succeeded > 0 ? "text-deny" : "text-approve"} />
    </div>
  );
}

function ago(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  return `${Math.round(s / 3600)}h`;
}

export function LiveFeed({ items, onSelect }: { items: Decision[]; onSelect: (d: Decision) => void }) {
  if (items.length === 0) return <p className="text-sm text-muted">No attempts yet. Be the first.</p>;
  return (
    <ul className="space-y-1.5">
      {items.slice(0, 8).map((d) => (
        <li key={d.decision_id}>
          <button
            type="button"
            onClick={() => onSelect(d)}
            className="flex w-full items-center justify-between gap-3 rounded-md px-1.5 py-1.5 text-left hover:bg-bg"
          >
            <span className="min-w-0">
              <span className="block text-[13px] text-ink">
                {d.customer_name ?? "Visitor"} <span className="text-muted">· {d.order_id}</span>
              </span>
              <span className="block font-mono text-[10px] text-muted">
                {d.tries ?? 1} {(d.tries ?? 1) === 1 ? "try" : "tries"} · {ago(d.created_at)} ago
                {d.gullible ? " · gullible" : ""}
              </span>
            </span>
            <OutcomeChip outcome={d.outcome} size="sm" />
          </button>
        </li>
      ))}
    </ul>
  );
}
