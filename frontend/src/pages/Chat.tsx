import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { DecisionPanel } from "../components/DecisionPanel";
import { DemoSleeping } from "../components/Layout";
import { PersonaPicker } from "../components/PersonaPicker";
import { useHealth, useMeta } from "../lib/hooks";
import { useConversation } from "../lib/useConversation";
import type { Persona } from "../types/decision";

// The six demo personas (docs/prd.md section 8).
const DEMO = ["CUST-007", "CUST-011", "CUST-015", "CUST-020", "CUST-023", "CUST-031"];

const GENUINE = [
  "My blue mug arrived cracked down the side. I have a photo. Can I get a refund for the mug?",
  "Hi! Where is my order?",
];

export function Chat() {
  const health = useHealth();
  const meta = useMeta();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [customer, setCustomer] = useState<string | null>("CUST-007");
  const convo = useConversation("chat");

  useEffect(() => {
    api.personas().then(setPersonas).catch(() => undefined);
  }, []);
  useEffect(() => {
    if (customer) convo.reset(customer, false);
  }, [customer]);

  if (health === "asleep" || health === "budget") return <DemoSleeping reason={health} />;
  const persona = personas.find((p) => p.customer_id === customer);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <p className="label mb-3"><span className="text-accent">chai &amp; clay</span> · customer support</p>
      <h1 className="text-4xl">Hi{persona ? ` ${persona.name}` : ""}, how can we help?</h1>
      <p className="mt-3 max-w-prose text-muted">
        This is the store's normal support chat. Every refund the assistant attempts is checked by Refund Guard first.
      </p>
      <div className="mt-6">
        <PersonaPicker personas={personas} selected={customer} onSelect={setCustomer} only={DEMO} />
      </div>
      <div className="mt-6 grid gap-5 md:grid-cols-[1.3fr_1fr] md:items-start">
        <ChatPanel
          messages={convo.messages}
          busy={convo.busy}
          disabled={convo.blocked}
          placeholder="Write a message…"
          suggestions={customer === "CUST-007" ? GENUINE : []}
          onSend={(t) => customer && convo.send(customer, false, t)}
          onSelectDecision={convo.setLatest}
        />
        <aside
          className="card scroll-slim p-5 md:sticky md:top-20 md:max-h-[calc(100dvh-6rem)] md:overflow-y-auto"
          aria-label="Why this decision"
        >
          <p className="label mb-4">why? · refund guard</p>
          {convo.latest ? (
            <DecisionPanel d={convo.latest} meta={meta} />
          ) : (
            <p className="text-sm text-muted">If the assistant tries a refund, you'll see exactly how it was checked.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
