import { inr } from "../lib/decision";
import type { Persona } from "../types/decision";

export function PersonaPicker({
  personas,
  selected,
  onSelect,
  only,
}: {
  personas: Persona[];
  selected: string | null;
  onSelect: (id: string) => void;
  only?: string[];
}) {
  const list = only ? personas.filter((p) => only.includes(p.customer_id)) : personas;
  return (
    <div className="flex gap-2 overflow-x-auto pb-1" role="radiogroup" aria-label="Pick a customer">
      {list.map((p) => {
        const o = p.orders[0];
        const active = p.customer_id === selected;
        return (
          <button
            key={p.customer_id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onSelect(p.customer_id)}
            className={`min-w-[150px] shrink-0 rounded-[10px] border px-3 py-2 text-left transition-colors ${
              active ? "border-accent bg-accent/10" : "border-hairline bg-surface hover:border-muted/50"
            }`}
          >
            <span className="block text-sm">{p.name}</span>
            {o && (
              <span className="block font-mono text-[11px] text-muted">
                {o.order_id} · {inr(o.order_amount)}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function ModeSwitch({ gullible, onChange }: { gullible: boolean; onChange: (g: boolean) => void }) {
  return (
    <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
      <div className="inline-flex rounded-[10px] border border-hairline p-0.5" role="radiogroup" aria-label="Chatbot mode">
        {[
          { v: false, label: "Normal bot" },
          { v: true, label: "Gullible bot" },
        ].map((o) => (
          <button
            key={o.label}
            type="button"
            role="radio"
            aria-checked={gullible === o.v}
            onClick={() => onChange(o.v)}
            className={`rounded-lg px-3 py-1.5 text-sm ${gullible === o.v ? "bg-ink text-bg" : "text-muted hover:text-ink"}`}
          >
            {o.label}
          </button>
        ))}
      </div>
      <p className="text-[12px] text-muted">
        {gullible
          ? "The chatbot tries every refund you ask for. Only Decider 2B stands in the way."
          : "A careful chatbot. Decider 2B checks every refund it tries."}
      </p>
    </div>
  );
}
