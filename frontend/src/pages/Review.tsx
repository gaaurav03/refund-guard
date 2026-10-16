import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, friendlyMessage } from "../api/client";
import { DecisionPanel } from "../components/DecisionPanel";
import { inr } from "../lib/decision";
import { useMeta } from "../lib/hooks";
import type { Decision } from "../types/decision";

const TOKEN_KEY = "rg-reviewer-token";

function readToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function Review() {
  const meta = useMeta();
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
  const [items, setItems] = useState<Decision[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<Decision | null>(null);
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setItems(await api.reviews(token));
      setError(null);
    } catch (e) {
      setError(friendlyMessage(e));
      setItems(null);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const signIn = (e: FormEvent) => {
    e.preventDefault();
    try {
      sessionStorage.setItem(TOKEN_KEY, draft);
    } catch {
      /* session-only storage unavailable; token kept in memory */
    }
    setToken(draft);
  };

  const resolve = async (action: "approve" | "deny") => {
    if (!open) return;
    setBusy(true);
    try {
      await api.resolve(token, open.decision_id, action, action === "approve" && amount ? Number(amount) : null, note);
      setOpen(null);
      setNote("");
      await load();
    } catch (e) {
      setError(friendlyMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 sm:px-6">
        <p className="label mb-3">store owner</p>
        <h1 className="mb-6 text-4xl">Review queue</h1>
        <form onSubmit={signIn} className="card space-y-3 p-5">
          <label htmlFor="token" className="text-sm text-muted">Reviewer token</label>
          <input
            id="token"
            type="password"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="min-h-[44px] w-full rounded-[10px] border border-hairline bg-bg px-3"
          />
          <button className="btn-primary w-full" type="submit" disabled={!draft}>Open queue</button>
        </form>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <p className="label mb-3">store owner</p>
      <h1 className="text-4xl">Review queue</h1>
      <p className="mt-3 max-w-prose text-muted">
        Refunds Refund Guard wasn't sure about. Nothing here has been paid. You decide.
      </p>
      {error && <p className="mt-6 rounded-card border border-deny/40 bg-deny/10 p-3 text-sm">{error}</p>}

      <div className="mt-8 grid gap-5 lg:grid-cols-[1fr_1fr]">
        <div className="card divide-y divide-hairline">
          {items === null && !error && <p className="p-5 font-mono text-[12px] text-muted">loading…</p>}
          {items?.length === 0 && (
            <div className="p-10 text-center">
              <p className="font-serif text-2xl">Queue clear ☕</p>
              <p className="mt-1 text-sm text-muted">Nothing needs a human right now.</p>
            </div>
          )}
          {items?.map((d) => (
            <button
              key={d.decision_id}
              type="button"
              onClick={() => {
                setOpen(d);
                setAmount(String(d.requested_amount));
              }}
              className={`flex w-full items-start justify-between gap-3 p-4 text-left hover:bg-bg ${
                open?.decision_id === d.decision_id ? "bg-bg" : ""
              }`}
            >
              <div className="min-w-0">
                <p className="font-mono text-[12px] text-muted">
                  {d.customer_id} · {d.order_id} · {new Date(d.created_at).toLocaleString()}
                </p>
                <p className="mt-1 truncate text-[14px]">{meta?.policy_steps[d.policy_step] ?? d.policy_step}</p>
              </div>
              <span className="shrink-0 font-mono text-sm">{inr(d.requested_amount)}</span>
            </button>
          ))}
        </div>

        <aside className="card p-5" aria-label="Review details">
          {open ? (
            <div className="space-y-5">
              <DecisionPanel d={open} meta={meta} />
              <div className="rule space-y-3 pt-4">
                <label className="block text-sm text-muted" htmlFor="amount">
                  Amount to refund (max {inr(open.requested_amount)})
                </label>
                <input
                  id="amount"
                  inputMode="decimal"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="min-h-[44px] w-full rounded-[10px] border border-hairline bg-bg px-3 font-mono"
                />
                <input
                  aria-label="Note"
                  placeholder="Note (optional)"
                  value={note}
                  maxLength={500}
                  onChange={(e) => setNote(e.target.value)}
                  className="min-h-[44px] w-full rounded-[10px] border border-hairline bg-bg px-3"
                />
                <div className="flex gap-3">
                  <button className="btn-primary flex-1" disabled={busy} onClick={() => resolve("approve")}>
                    Approve refund
                  </button>
                  <button className="btn-ghost flex-1" disabled={busy} onClick={() => resolve("deny")}>
                    Deny
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted">Select a request to see the evidence and Decider's answers.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
