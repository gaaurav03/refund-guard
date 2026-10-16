import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { DecisionPanel } from "../components/DecisionPanel";
import { DemoSleeping } from "../components/Layout";
import { ModeSwitch, PersonaPicker } from "../components/PersonaPicker";
import { MissionCard } from "../components/MissionCard";
import { LiveFeed, Scoreboard } from "../components/Scoreboard";
import { useHealthDetail, useMeta, usePoll } from "../lib/hooks";
import { MISSIONS } from "../lib/missions";
import { savedSelection, useConversation } from "../lib/useConversation";
import type { Persona } from "../types/decision";

type Tab = "chat" | "decision" | "score";

export function Try() {
  const { state: health, deciderOk } = useHealthDetail();
  const meta = useMeta();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const restored = savedSelection("challenge"); // a refresh brings back the same customer, mode and chat
  const [customer, setCustomer] = useState<string | null>(restored?.customerId ?? null);
  const [gullible, setGullible] = useState(restored?.gullible ?? true);
  const [tab, setTab] = useState<Tab>("chat");
  const convo = useConversation("challenge");
  const score = usePoll(api.scoreboard, 3000, health === "up");
  const feed = usePoll(() => api.live(), 3000, health === "up");

  useEffect(() => {
    api.personas().then((p) => {
      setPersonas(p);
      setCustomer((c) => c ?? p.find((x) => x.customer_id === "CUST-011")?.customer_id ?? p[0]?.customer_id ?? null);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (customer) convo.reset(customer, gullible);
  }, [customer, gullible]);

  useEffect(() => {
    if (convo.latest) setTab((t) => (t === "chat" ? t : "decision"));
  }, [convo.latest]);

  if (health === "asleep" || health === "budget") return <DemoSleeping reason={health} />;

  const persona = personas.find((p) => p.customer_id === customer);
  const order = persona?.orders[0];
  const won = convo.latest?.is_scam_success;
  const mission = customer ? MISSIONS[customer] : undefined;

  const tabs: [Tab, string][] = [["chat", "Chat"], ["decision", "Decision"], ["score", "Score"]];

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <p className="label mb-3"><span className="text-accent">try it</span> · the challenge</p>
      <h1 className="text-4xl sm:text-5xl">Try to scam our bot.</h1>
      <p className="mt-3 max-w-prose text-muted">
        Pick a customer and read their mission: what really happened, and the refund you're trying to get anyway. Lie,
        pressure, inject instructions: anything goes. Refunds are simulated; no real money moves.
      </p>

      <div className="mt-8 space-y-4">
        <PersonaPicker personas={personas} selected={customer} onSelect={setCustomer} />
        <ModeSwitch gullible={gullible} onChange={setGullible} />
        {persona && mission && <MissionCard persona={persona} mission={mission} />}
      </div>

      {deciderOk === false && (
        <div role="status" className="mt-6 rounded-card border border-escalate/40 bg-escalate/10 p-4 text-sm">
          <span className="font-medium">Decider 2B is offline right now.</span> Every refund attempt will fail closed
          and go to a human (nothing is paid). Try again in a few minutes.
        </div>
      )}

      {won && (
        <div className="mt-6 rounded-card border border-deny/40 bg-deny/10 p-4 text-sm">
          <span className="font-medium">You beat it.</span> That refund shouldn't have been paid. It's now on the public
          scoreboard and goes into our benchmark as a failure case. Thank you.
        </div>
      )}

      {/* mobile tabs */}
      <div className="mt-8 flex gap-1 rounded-[10px] border border-hairline p-0.5 lg:hidden" role="tablist">
        {tabs.map(([t, l]) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-lg py-2 text-sm ${tab === t ? "bg-ink text-bg" : "text-muted"}`}
          >
            {l}
            {t === "decision" && convo.latest && tab !== "decision" && <span className="ml-1 text-accent">●</span>}
          </button>
        ))}
      </div>

      <div className="mt-4 grid gap-5 lg:mt-8 lg:grid-cols-[1.15fr_1fr_0.75fr] lg:items-start">
        <section className={`${tab === "chat" ? "" : "hidden"} lg:block`} aria-label="Chat">
          <ChatPanel
            messages={convo.messages}
            busy={convo.busy}
            disabled={convo.blocked ?? (customer ? null : "Pick a customer first")}
            placeholder={order ? `Talk to Chai & Clay support about ${order.order_id}…` : "Pick a customer"}
            suggestions={mission?.starters ?? []}
            onSend={(t) => customer && convo.send(customer, gullible, t)}
            onSelectDecision={(d) => {
              convo.setLatest(d);
              setTab("decision");
            }}
          />
          <div className="mt-2 flex items-center justify-between font-mono text-[11px] text-muted">
            <span>{convo.left !== null ? `${convo.left} messages left` : ""}</span>
            {convo.messages.length > 0 && customer && (
              <button
                type="button"
                onClick={() => convo.reset(customer, gullible, true)}
                disabled={convo.busy}
                className="hover:text-ink disabled:opacity-50"
              >
                ↺ new chat
              </button>
            )}
          </div>
        </section>

        <section
          className={`card scroll-slim p-5 ${tab === "decision" ? "" : "hidden"} lg:sticky lg:top-20 lg:block lg:max-h-[calc(100dvh-6rem)] lg:overflow-y-auto`}
          aria-label="Live decision"
        >
          <p className="label mb-4">live decision</p>
          {convo.latest ? (
            <DecisionPanel d={convo.latest} meta={meta} />
          ) : (
            <div className="space-y-3 font-mono text-[12px] text-muted">
              <p>Waiting for a refund attempt…</p>
              <p className="leading-relaxed">
                When the chatbot calls <span className="text-ink">issue_refund</span>, the guard's full readout appears here:
                pre-checks, key facts, Decider's six answers, and the outcome.
              </p>
            </div>
          )}
        </section>

        <section
          className={`scroll-slim space-y-5 ${tab === "score" ? "" : "hidden"} lg:sticky lg:top-20 lg:block lg:max-h-[calc(100dvh-6rem)] lg:overflow-y-auto`}
          aria-label="Scoreboard"
        >
          <div className="card p-5">
            <p className="label mb-2">scoreboard · all visitors</p>
            <Scoreboard score={score} />
          </div>
          <div className="card p-5">
            <p className="label mb-3">recent attempts</p>
            <LiveFeed
              items={feed ?? []}
              onSelect={(d) => {
                convo.setLatest(d);
                setTab("decision");
              }}
            />
          </div>
        </section>
      </div>
    </div>
  );
}
