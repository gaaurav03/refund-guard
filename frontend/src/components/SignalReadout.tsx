import { useEffect, useState } from "react";
import { decidingSignal, fires } from "../lib/decision";
import type { Meta, Signals } from "../types/decision";

/** Decider's six yes/no answers as an instrument readout: bar, threshold tick, value. */
export function SignalReadout({
  signals,
  meta,
  policyStep,
  compact = false,
}: {
  signals: Signals;
  meta: Meta;
  policyStep: string;
  compact?: boolean;
}) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setShown(true), 30); // bars animate from 0 to their value
    return () => window.clearTimeout(t);
  }, [signals]);
  const deciding = decidingSignal(policyStep);

  return (
    <ul className={`${compact ? "space-y-1" : "space-y-2.5"} font-mono text-[12px]`} aria-label="Decider signals">
      {meta.signals.map((s) => {
        const value = signals[s.name] ?? 0;
        const hot = fires(s, value);
        const isDeciding = s.name === deciding;
        return (
          <li
            key={s.name}
            data-testid={`signal-${s.name}`}
            data-deciding={isDeciding || undefined}
            className={`rounded-md px-2 ${compact ? "py-1" : "py-1.5"} transition-colors ${isDeciding ? "bg-accent/10 ring-1 ring-accent/40" : ""}`}
          >
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <span className={`truncate ${isDeciding ? "text-ink" : "text-muted"}`} title={s.instructions}>
                {isDeciding && <span className="mr-1 text-accent" aria-hidden>▸</span>}
                {s.label}
              </span>
              <span className={`tabular-nums ${hot ? "text-accent" : "text-muted"}`}>{value.toFixed(2)}</span>
            </div>
            <div className="relative h-1.5 rounded-full bg-hairline">
              <div
                className={`bar-fill absolute inset-y-0 left-0 rounded-full ${hot ? "bg-accent" : "bg-muted/60"}`}
                style={{ width: shown ? `${Math.round(value * 100)}%` : "0%" }}
              />
              <div
                className="absolute -top-1 h-3.5 w-px bg-ink/60"
                style={{ left: `${s.threshold * 100}%` }}
                title={`threshold ${s.threshold} (${s.fires_when === "below" ? "fires below" : "fires at or above"})`}
                data-testid={`tick-${s.name}`}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
