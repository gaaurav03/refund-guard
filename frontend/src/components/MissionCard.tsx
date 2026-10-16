import type { Mission } from "../lib/missions";
import { inr } from "../lib/decision";
import type { Persona } from "../types/decision";

const KIND_STYLE: Record<Mission["kind"], string> = {
  honest: "border-approve/40 text-approve",
  borderline: "border-escalate/40 text-escalate",
  "false claim": "border-deny/40 text-deny",
  "social engineering": "border-deny/40 text-deny",
  "prompt injection": "border-deny/40 text-deny",
  "over-ask": "border-partial/40 text-partial",
};

/** The visitor's briefing. Shown on the page only: the chatbot and the guard never see it. */
export function MissionCard({ persona, mission }: { persona: Persona; mission: Mission }) {
  const order = persona.orders[0];
  return (
    <section className="card p-5" aria-label={`Mission for ${persona.name}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h2 className="font-serif text-2xl">{persona.name}</h2>
        <span className={`rounded-full border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide ${KIND_STYLE[mission.kind]}`}>
          {mission.kind}
        </span>
        <span className="font-mono text-[12px] text-muted" title="difficulty">
          {"★".repeat(mission.difficulty)}
          <span className="opacity-30">{"★".repeat(3 - mission.difficulty)}</span>
        </span>
        {order && (
          <span className="ml-auto font-mono text-[12px] text-muted">
            {order.order_id} · {order.items.map((i) => `${i.qty}× ${i.name}`).join(", ")} · {inr(order.order_amount)}
          </span>
        )}
      </div>
      <dl className="mt-4 grid gap-4 text-[14px] sm:grid-cols-3">
        <div>
          <dt className="label mb-1">What really happened</dt>
          <dd className="leading-relaxed">{mission.truth}</dd>
        </div>
        <div>
          <dt className="label mb-1">Your mission</dt>
          <dd className="leading-relaxed">{mission.mission}</dd>
        </div>
        <div>
          <dt className="label mb-1">You win if</dt>
          <dd className="leading-relaxed">{mission.win}</dd>
        </div>
      </dl>
      <p className="mt-4 font-mono text-[11px] text-muted">
        Only you see this card. The chatbot and Decider only see the shop's records and what you type.
      </p>
    </section>
  );
}
