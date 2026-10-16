import { explain, inr } from "../lib/decision";
import type { Decision, Meta } from "../types/decision";
import { OutcomeChip } from "./OutcomeChip";
import { SignalReadout } from "./SignalReadout";

/** The full guard readout for one issue_refund attempt. */
export function DecisionPanel({ d, meta }: { d: Decision; meta: Meta | null }) {
  return (
    <div className="space-y-4" data-testid="decision-panel">
      <div className="font-mono text-[12px] text-muted">
        <span className="text-ink">issue_refund</span>({d.order_id}, {inr(d.requested_amount)})
        {d.gullible && <span className="ml-2 rounded border border-hairline px-1.5 py-0.5 text-[10px] uppercase">gullible</span>}
      </div>

      <div>
        <p className="label mb-1.5">Pre-checks</p>
        <p className="font-mono text-[12px]">
          {d.decided_by === "precheck" ? (
            <span className="text-deny">✕ {d.rule_id} fired</span>
          ) : (
            <span className="text-approve">✓ 9/9 passed</span>
          )}
        </p>
      </div>

      {d.key_facts.length > 0 && (
        <div>
          <p className="label mb-1.5">Key facts (from store records)</p>
          <ul className="space-y-1 text-[13px] leading-snug text-ink/90">
            {d.key_facts.map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-muted" aria-hidden>·</span>
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {d.signals && meta ? (
        <div>
          <p className="label mb-1.5">Decider 2B · six yes/no answers</p>
          <SignalReadout signals={d.signals} meta={meta} policyStep={d.policy_step} />
        </div>
      ) : (
        d.decided_by === "precheck" && <p className="font-mono text-[12px] text-muted">Decider not needed.</p>
      )}

      <div className="rule pt-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <OutcomeChip outcome={d.outcome} amount={d.approved_amount} />
          <span className="font-mono text-[11px] text-muted">{(d.decision_latency_ms / 1000).toFixed(1)} s</span>
        </div>
        <p className="mt-2 text-[13px] text-muted">{explain(d, meta)}</p>
      </div>
    </div>
  );
}
